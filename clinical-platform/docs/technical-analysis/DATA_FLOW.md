# Clinical Platform — Data Flow Analysis (数据流分析)

## 1. Authentication Flow (认证流程)

```
┌──────────┐     ┌──────────────┐     ┌──────────┐     ┌────────────┐
│ Browser  │────▶│ Express      │────▶│ bcrypt   │────▶│ PostgreSQL │
│          │     │ /auth/login  │     │ compare  │     │ users      │
└──────────┘     └──────┬───────┘     └──────────┘     └────────────┘
                        │
                        ▼
                 ┌──────────────┐
                 │ JWT Sign     │
                 │ (15min + 7d) │
                 └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │ Response:    │
                 │ {user, token,│
                 │  refreshToken│
                 │  Set-Cookie} │
                 └──────────────┘
```

### Step-by-step (auth.js:38-65)

1. **Input validation** (auth.js:40-42): Checks `email` and `password` present
2. **User lookup** (auth.js:44-47): `SELECT id, email, password_hash, full_name, role, clinic_id FROM users WHERE email = $1 AND deleted_at IS NULL`
3. **Password verification** (auth.js:52): `bcrypt.compare(password, user.password_hash)` — cost factor 12
4. **Token generation** (auth.js:56-57):
   - Access token: `{ id, email, role, clinic_id }` → 15min expiry
   - Refresh token: `{ id, type: 'refresh' }` → 7 day expiry
5. **Cookie + response** (auth.js:59-60): Sets httpOnly cookie + JSON body

[VERIFY: clinical-platform/backend/express/src/routes/auth.js:38-65]
[VERIFY: clinical-platform/backend/express/src/middleware/auth.js:20-33]

---

## 2. Proxy Auth Context Flow (代理认证上下文流)

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────┐
│ Browser  │────▶│ Express      │────▶│ Proxy        │────▶│ FastAPI  │
│ Bearer   │     │ authenticate │     │ onProxyReq   │     │ get_     │
│ token    │     │ middleware   │     │ inject hdrs  │     │ user_ctx │
└──────────┘     └──────┬───────┘     └──────────────┘     └──────────┘
                        │ jwt.verify
                        ▼
                 ┌──────────────┐
                 │ req.user =   │
                 │ {id, email,  │
                 │  role,       │
                 │  clinic_id}  │
                 └──────────────┘
```

### Step-by-step (proxy.js:6-25)

1. **JWT verification** (proxy.js:9): `authenticate` middleware extracts token from cookie or Authorization header
2. **JWT decode** (auth.js:12): `jwt.verify(token, JWT_SECRET)` → populates `req.user`
3. **Header injection** (proxy.js:16-19):
   - `x-user-id` ← `req.user.id`
   - `x-user-role` ← `req.user.role`
   - `x-clinic-id` ← `req.user.clinic_id`
4. **FastAPI extraction** (auth_context.py:11-22):
   - Reads `x-user-id`, `x-user-role`, `x-clinic-id` from request headers
   - Constructs `UserContext(user_id, role, clinic_id)`
   - Raises 401 if headers missing, 400 if invalid UUID

[VERIFY: clinical-platform/backend/express/src/routes/proxy.js:15-20]
[VERIFY: clinical-platform/backend/fastapi/app/services/auth_context.py:11-22]

---

## 3. Patient CRUD Flow (患者 CRUD 流)

### 3.1 Create Patient

```
Browser → POST /api/patients
  │  Body: {first_name, last_name, DOB, gender, ...}
  │
  ├─ Express: authenticate → proxy → headers
  │
  └─ FastAPI patients.py:create_patient()
      ├─ Validate: user.clinic_id exists → 400 if not
      ├─ Build INSERT:
      │   clinic_id = user.clinic_id (from proxy header)
      │   created_by = user.user_id (from proxy header)
      ├─ SQL: INSERT INTO patients (...) RETURNING *
      ├─ db.commit()
      └─ Return PatientResponse
```

[VERIFY: clinical-platform/backend/fastapi/app/api/patients.py:31-47]

### 3.2 List Patients (Clinic-Scoped)

```
Browser → GET /api/patients?search=&skip=0&limit=50
  │
  └─ FastAPI patients.py:list_patients()
      ├─ WHERE deleted_at IS NULL
      ├─ AND clinic_id = :clinic_id  (if user has clinic)
      ├─ AND (first_name ILIKE :search OR last_name ILIKE :search)
      ├─ ORDER BY created_at DESC
      ├─ LIMIT :limit OFFSET :skip
      └─ Return List[PatientResponse]
```

[VERIFY: clinical-platform/backend/fastapi/app/api/patients.py:12-29]

### 3.3 Clinic Isolation

Every patient endpoint enforces clinic scoping:
```python
if user.clinic_id and row["clinic_id"] != user.clinic_id:
    raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", ...})
```

[VERIFY: clinical-platform/backend/fastapi/app/api/patients.py:62-63 — get_patient]
[VERIFY: clinical-platform/backend/fastapi/app/api/dental.py:114-115 — get_dental_chart]
[VERIFY: clinical-platform/backend/fastapi/app/api/orthopedic.py:177-178 — get_skeleton]

---

## 4. Dental Chart Data Flow (牙科图表数据流)

### 4.1 Get Dental Chart

```
Browser → GET /api/patients/{id}/dental-chart
  │
  └─ FastAPI dental.py:get_dental_chart()
      │
      ├─ Step 1: Patient access check (lines 108-115)
      │   SELECT clinic_id FROM patients WHERE id=:pid AND deleted_at IS NULL
      │   → Verify clinic_id matches
      │
      ├─ Step 2: _ensure_chart() (lines 71-98)
      │   ├─ SELECT id FROM dental_charts WHERE patient_id=:pid
      │   ├─ If not exists:
      │   │   ├─ INSERT INTO dental_charts (patient_id) → chart_id
      │   │   ├─ For each FDI in all_permanent_fdi() [11..48]:
      │   │   │   └─ INSERT INTO teeth (dental_chart_id, tooth_number_fdi, ...)
      │   │   └─ db.commit()
      │   └─ Return chart_id
      │
      ├─ Step 3: Fetch teeth (lines 119-123)
      │   SELECT id, tooth_number_fdi, dentition_type, position_in_quadrant, quadrant
      │   FROM teeth WHERE dental_chart_id=:cid ORDER BY tooth_number_fdi
      │
      ├─ Step 4: Fetch latest events (lines 126-132)
      │   SELECT DISTINCT ON (tooth_id) ...
      │   FROM tooth_events WHERE patient_id=:pid AND status='active'
      │   ORDER BY tooth_id, event_date DESC, created_at DESC
      │
      ├─ Step 5: Merge + enrich (lines 134-161)
      │   For each tooth:
      │   ├─ Look up latest_event from events_by_tooth map
      │   ├─ Convert FDI → Universal → Palmer (numbering.py)
      │   ├─ Derive state from event_type (dental.py:56-68)
      │   └─ Build ToothOut with all numbering systems
      │
      └─ Return DentalChartOut{id, patient_id, teeth[]}
```

[VERIFY: clinical-platform/backend/fastapi/app/api/dental.py:101-161]

### 4.2 Create Tooth Event

```
Browser → POST /api/patients/{pid}/dental-chart/teeth/{tid}/events
  │  Body: {event_type, procedure_name?, diagnosis?, event_date?, surfaces?, notes?}
  │
  └─ FastAPI dental.py:create_tooth_event()
      ├─ Verify tooth belongs to patient (lines 207-212)
      │   SELECT id FROM teeth WHERE id=:tid AND dental_chart_id IN
      │     (SELECT id FROM dental_charts WHERE patient_id=:pid)
      │
      ├─ Validate event_type (lines 214-216)
      │   Must be one of: exam, caries, restoration, extraction,
      │   root_canal, crown, implant, fracture, cleaning, other
      │
      ├─ INSERT INTO tooth_events (lines 230-235)
      │   tooth_id, patient_id, event_type, procedure_name,
      │   diagnosis, event_date, surfaces, provider_id, notes, created_by
      │
      ├─ db.commit()
      └─ Return ToothEventOut
```

[VERIFY: clinical-platform/backend/fastapi/app/api/dental.py:198-243]

---

## 5. Orthopedic Chart Data Flow (骨科图表数据流)

### 5.1 Get Skeleton

```
Browser → GET /api/patients/{id}/skeleton
  │
  └─ FastAPI orthopedic.py:get_skeleton()
      │
      ├─ Patient access check (lines 171-178)
      │
      ├─ _ensure_skeleton() (lines 125-162)
      │   ├─ Check if orthopedic_charts exists for patient
      │   ├─ If not:
      │   │   ├─ INSERT INTO orthopedic_charts → chart_id
      │   │   ├─ For each region in STANDARD_BODY_REGIONS (26 regions):
      │   │   │   ├─ INSERT INTO body_regions → region_id
      │   │   │   └─ For each bone in BONES_PER_REGION[region_code]:
      │   │   │       └─ INSERT INTO bones → bone
      │   │   └─ db.commit()
      │   └─ Return chart_id
      │
      ├─ Fetch regions (lines 182-185)
      │   SELECT id, region_name, region_code, side, svg_path
      │   FROM body_regions WHERE orthopedic_chart_id=:cid
      │
      ├─ Fetch bones (lines 187-192)
      │   SELECT b.id, b.bone_name, b.bone_code, b.side, b.body_region_id
      │   FROM bones b JOIN body_regions r ON ...
      │
      ├─ Fetch latest events (lines 194-200)
      │   SELECT DISTINCT ON (bone_id) ...
      │   FROM bone_events WHERE patient_id=:pid AND status='active'
      │
      ├─ Merge (lines 202-229)
      │   Group bones by region, attach latest_event, derive state
      │
      └─ Return SkeletonOut{id, patient_id, body_regions[]}
```

[VERIFY: clinical-platform/backend/fastapi/app/api/orthopedic.py:165-229]

### 5.2 Standard Body Regions (26 regions)

Each region has pre-defined SVG paths for interactive rendering (orthopedic.py:16-44):

```
Region Code     │ Side      │ Description
────────────────┼───────────┼──────────────
head            │ midline   │ Skull
cervical        │ midline   │ Neck (Cervical Spine)
shoulder        │ left/right│ Shoulder
upper_arm       │ left/right│ Upper Arm
elbow           │ left/right│ Elbow
lower_arm       │ left/right│ Lower Arm
hand            │ left/right│ Hand
thoracic        │ midline   │ Thoracic Spine
lumbar          │ midline   │ Lumbar Spine
sacrum          │ midline   │ Sacrum
ribs            │ bilateral │ Ribs
pelvis          │ midline   │ Pelvis
hip             │ left/right│ Hip
upper_leg       │ left/right│ Upper Leg
knee            │ left/right│ Knee
lower_leg       │ left/right│ Lower Leg
foot            │ left/right│ Foot
```

---

## 6. Drug Intelligence Flow (药物情报流)

### 6.1 Drug Resolution

```
Browser → POST /api/drugs/resolve
  │  Body: {name: "Aspirin"}
  │
  └─ FastAPI drugs.py:resolve_drug()
      │
      ├─ RxNormProvider.resolve("Aspirin") (rxnorm.py:43-84)
      │   ├─ Not numeric? → search("Aspirin", limit=1)
      │   │   └─ GET rxnav.nlm.nih.gov/REST/approximateTerm.json
      │   │       → candidates[0].rxcui → recursive resolve(cui)
      │   │
      │   ├─ GET /rxcui/{cui}/property.json → RxNorm Name
      │   ├─ GET /rxcui/{cui}/related.json?tty=IN+MIN+BN → ingredients + brand names
      │   │   └─ drug_class = VA concept name (if present)
      │   │
      │   └─ Return DrugConcept{rxnorm_cui, name, drug_class, aliases}
      │
      └─ Return ResolveResponse
```

[VERIFY: clinical-platform/backend/fastapi/app/services/drugs/rxnorm.py:43-84]
[VERIFY: clinical-platform/backend/fastapi/app/api/drugs.py:30-39]

### 6.2 Drug Interaction Check

```
Browser → POST /api/drug-interactions/check
  │  Body: {drugs: ["Aspirin", "Warfarin"]}
  │
  └─ FastAPI drugs.py:check_interactions()
      │
      ├─ Validate: len(drugs) >= 2 → 400 if not
      │
      └─ DrugInteractionService.check() (interactions.py:37-98)
          │
          ├─ Step 1: Resolve each drug (lines 40-66)
          │   For each name:
          │   ├─ provider.resolve(name) → DrugConcept
          │   ├─ UPSERT drug_concepts (ON CONFLICT UPDATE)
          │   ├─ UPSERT drug_aliases (up to 5 aliases)
          │   └─ Collect resolved CUIs
          │
          ├─ Step 2: Check all pairs (lines 68-91)
          │   For each pair (i, j) where i < j:
          │   ├─ Sort CUIs: a = min(cuis[i], cuis[j])
          │   ├─ Query drug_interactions JOIN drug_concepts
          │   │   WHERE dc_a.rxnorm_cui = :a AND dc_b.rxnorm_cui = :b
          │   └─ Collect DrugInteraction objects
          │
          ├─ Step 3: Warnings (lines 93-96)
          │   Report unresolved drug names
          │
          └─ Return InteractionCheckResult
```

[VERIFY: clinical-platform/backend/fastapi/app/services/drugs/interactions.py:37-98]
[VERIFY: clinical-platform/database/migrations/005_drugs.sql:31 — CHECK (drug_a_id < drug_b_id)]

**Note**: The canonical ordering `drug_a_id < drug_b_id` ensures each pair is stored exactly once. The check `sorted([cuis[i], cuis[j]])` aligns with this constraint.

---

## 7. RAG Pipeline Flow (RAG 管道流)

### 7.1 Hybrid Retrieval

```
User Query (e.g., "What are drug interactions for this patient's medications?")
  │
  ├─▶ HybridRetriever.retrieve() (retrieval.py:52-78)
  │   │
  │   ├─ _local_search() (lines 23-43)
  │   │   ├─ embed_text(query) → 1536-dim vector
  │   │   │   ├─ Try: SentenceTransformer("all-MiniLM-L6-v2")
  │   │   │   │   → model.encode(text).tolist()
  │   │   │   │   → Pad/truncate to 1536 dimensions
  │   │   │   └─ Fallback: _hash_embed() → deterministic pseudo-embedding
  │   │   │
  │   │   ├─ SQL (pgvector cosine similarity):
  │   │   │   SELECT id, content, metadata,
  │   │   │          1 - (embedding <=> CAST(:emb AS vector)) AS similarity
  │   │   │   FROM knowledge_chunks
  │   │   │   WHERE embedding IS NOT NULL
  │   │   │   [AND patient_id filter if scoped]
  │   │   │   ORDER BY embedding <=> CAST(:emb AS vector)
  │   │   │   LIMIT :k
  │   │   │
  │   │   └─ Return List[RetrievedChunk]
  │   │
  │   ├─ _tavily_search() (lines 45-50)
  │   │   ├─ POST https://api.tavily.com/search
  │   │   │   {api_key, query, max_results, topic: "general"}
  │   │   ├─ Parse results → List[RetrievedChunk]
  │   │   └─ Graceful fallback: return [] if API key missing
  │   │
  │   └─ Reciprocal Rank Fusion (lines 62-78)
  │       │
  │       ├─ k = 60 (standard RRF constant)
  │       │
  │       ├─ For each local result at rank r:
      │       │   score[key] += 1.0 / (k + r + 1)
      │       │
      │       ├─ For each tavily result at rank r:
      │       │   score[key] += 1.0 / (k + r + 1)
      │       │
      │       └─ Sort by fused score → Return top_k
  │
  └─▶ PatientAssistant.chat() synthesizes response
```

[VERIFY: clinical-platform/backend/fastapi/app/rag/retrieval.py:52-78]
[VERIFY: clinical-platform/backend/fastapi/app/rag/embeddings.py:41-54]
[VERIFY: clinical-platform/backend/fastapi/app/rag/retrieval.py:62-77 — RRF fusion]

### 7.2 RRF Score Calculation

**Formula**: `RRF_score(d) = Σ 1/(k + rank_i(d) + 1)` where k=60

**Example**: If "Aspirin interaction" appears at rank 0 locally and rank 2 in Tavily:
```
RRF = 1/(60+0+1) + 1/(60+2+1) = 1/61 + 1/63 = 0.01639 + 0.01587 = 0.03226
```

**Key property**: Documents appearing in both result sets get boosted (summed scores).

---

## 8. AI Chat Synthesis Flow (AI 聊天综合流)

### 8.1 Patient Context Gathering

```
PatientAssistant._gather_patient_context() (patient_assistant.py:47-86)
  │
  ├─ Query 1: Patient identity
  │   SELECT first_name, last_name, DOB, gender FROM patients WHERE id=:pid
  │
  ├─ Query 2: Medications
  │   SELECT drug_name, dosage, frequency, status FROM medications WHERE patient_id=:pid
  │
  ├─ Query 3: Allergies
  │   SELECT allergen, severity, reaction FROM allergies WHERE patient_id=:pid
  │
  ├─ Query 4: Medical history
  │   SELECT condition_name, status FROM medical_histories WHERE patient_id=:pid
  │
  ├─ Query 5: Recent dental events
  │   SELECT tooth_id, event_type, procedure_name, event_date, diagnosis
  │   FROM tooth_events WHERE patient_id=:pid ORDER BY event_date DESC LIMIT 10
  │
  └─ Query 6: Recent bone events
      SELECT bone_id, event_type, diagnosis, event_date, treatment
      FROM bone_events WHERE patient_id=:pid ORDER BY event_date DESC LIMIT 10
```

[VERIFY: clinical-platform/backend/fastapi/app/ai/patient_assistant.py:47-86]

### 8.2 Response Synthesis (Rule-Based)

```
PatientAssistant.chat() (patient_assistant.py:88-156)
  │
  ├─ Gather context (6 DB queries)
  │
  ├─ Retrieve evidence (RAG pipeline)
  │   chunks = retriever.retrieve(db, message, patient_id, top_k=5)
  │
  ├─ Build citations from chunks (lines 99-106)
  │   For each chunk:
  │   └─ Citation(source, title, url, evidence_excerpt[:280])
  │
  ├─ Synthesize summary (lines 116-128)
  │   "Patient is {name} • DOB {dob} • {N} medications • {M} allergies • ..."
  │
  ├─ Clinical safety notes (lines 131-139)
  │   "This response is decision-support information..."
  │   "It is NOT a diagnosis or prescription."
  │   If no chunks: "No supporting external evidence..."
  │
  └─ Return PatientChatResponse
      ├─ patient_name, patient_id, summary
      ├─ dental_history, orthopedic_history
      ├─ recent_procedures, current_medications, allergies
      ├─ important_notes, missing_information
      └─ citations[]
```

[VERIFY: clinical-platform/backend/fastapi/app/ai/patient_assistant.py:88-156]

**Clinical safety language** (patient_assistant.py:6-7):
> "Clinical safety: this is decision-support. Outputs use 'based on', 'evidence indicates', 'no supporting record was found' language — never diagnosis or prescription."

---

## 9. Audit Log Flow (审计日志流)

```
Any /api/* Request
  │
  ├─ audit.js:auditMiddleware() fires on res 'finish' event
  │
  ├─ Compute: duration = Date.now() - start
  │
  ├─ Skip if: !req.path.startsWith('/api/')
  │
  ├─ INSERT INTO audit_logs:
  │   user_id: req.user?.id (null for unauthenticated)
  │   action: "{METHOD} {path}" (e.g. "GET /api/patients")
  │   resource_type: path.split('/')[2] (e.g. "patients")
  │   resource_id: req.params?.id
  │   success: res.statusCode < 400
  │   ip_address: req.ip
  │   metadata: { duration_ms, status: res.statusCode }
  │
  └─ Error logged but not propagated (silent failure)
```

[VERIFY: clinical-platform/backend/express/src/middleware/audit.js:1-30]

---

## 10. Frontend SPA Routing Flow (前端 SPA 路由流)

```
Browser loads index.html
  │
  ├─ <script type="module" src="js/app.js">
  │
  └─ new App()
      │
      ├─ Check localStorage('role')
      │   ├─ null → RoleSelection page
      │   │   └─ On select: save role → re-render
      │   │
      │   ├─ Set, check localStorage('token')
      │   │   ├─ null → AuthPage (login/register)
      │   │   │   └─ On success: save token → re-render
      │   │   │
      │   │   └─ Set → Dashboard
      │   │       ├─ Show role-based UI (dentist vs orthopedist)
      │   │       ├─ Navigation cards:
      │   │       │   Patients, Dental/Skeleton Chart,
      │   │       │   Drug Checker, AI Assistant, Appointments, History
      │   │       └─ Logout: clear localStorage → reload
```

[VERIFY: clinical-platform/frontend/js/app.js:1-33]

---

## 11. Data Transformation Points (数据转换点)

| Source | Transform | Destination | Location |
|--------|-----------|-------------|----------|
| Raw password | bcrypt hash (cost 12) | users.password_hash | auth.js:22 |
| JWT payload | jwt.sign() | Token string | auth.js:21-25 |
| DB row | dict(row._mapping) | Python dict | patients.py:29 |
| Pydantic model | .model_dump() | dict for SQL params | patients.py:39 |
| FDI number | fdi_to_universal() | ADA Universal string | dental.py:142 |
| FDI number | fdi_to_palmer() | Palmer notation string | dental.py:143 |
| event_type | _derive_state() | Visual state string | dental.py:56-68 |
| event_type | _derive_bone_state() | Visual state string | orthopedic.py:109-122 |
| Query text | embed_text() | 1536-dim float vector | embeddings.py:41-54 |
| pgvector similarity | 1 - (embedding <=> vector) | Cosine similarity score | retrieval.py:29 |
| Local + Tavily results | RRF fusion | Sorted combined list | retrieval.py:62-78 |
| Patient context + RAG chunks | Rule-based synthesis | PatientChatResponse | patient_assistant.py:116-155 |
| SVG path strings | Browser SVG rendering | Interactive body diagram | skeleton-svg.js:34-41 |
