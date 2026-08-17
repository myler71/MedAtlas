# Clinical Platform Design Spec

> **Date:** 2026-08-17
> **Status:** Approved (resumed reconstruction)
> **Classification:** Architectural
> **Goal:** Functional demo of a unified Dental + Orthopedics + Pharmaceutical RAG clinical platform

---

## 1. Product Vision

A unified clinical information, visualization, documentation, and decision-support platform for **Dentists and Orthopedists**. The doctor can manage patients, interact with visual clinical charts (odontogram, skeleton), check drug-drug interactions via RAG, and query an AI assistant about patient records.

**Not:** An autonomous diagnosis or prescribing system.

---

## 2. Target Users

- **Dentists** — primary interaction: dental chart, patient management, drug checker, AI assistant
- **Orthopedists** — primary interaction: skeleton chart, patient management, drug checker, AI assistant
- Both share the same patient database and core features

---

## 3. Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Vanilla HTML/CSS/JS | No build step, no framework |
| API Gateway | Express.js (Node) | Auth, RBAC, CORS, rate limiting, audit, proxy |
| Clinical/AI Backend | FastAPI (Python) | Patient CRUD, dental/orthopedic APIs, RAG, AI |
| Database | PostgreSQL + pgvector | System of record + vector search |
| Cache/Queue | Redis | Session cache, rate limiting |
| RAG Retrieval | **Tavily MCP** | Web-grounded search for drug/clinical knowledge |
| Drug Data | RxNorm API | Drug normalization, canonical identifiers |
| Containerization | Docker Compose | Local dev orchestration |

> **Note:** Tavily MCP replaces the originally proposed Groq API as the RAG retrieval provider. API keys will be supplied at final demo time and stored in `.env` (placeholder values during scaffolding).

---

## 4. System Architecture

```
                    Frontend (HTML/CSS/JS)
                           │
                           ↓
                    API Gateway (Express.js :3000)
                    ├── JWT Authentication
                    ├── RBAC Middleware
                    ├── Audit Logging Middleware
                    ├── CORS Configuration
                    ├── Rate Limiting
                    └── Route Proxying
                           │
              ┌────────────┼────────────┐
              ↓            ↓            ↓
         FastAPI       FastAPI      FastAPI
         (Auth svc)  (Clinical)   (AI/RAG)
         :8000        :8000        :8000
              │            │            │
              └────────────┼────────────┘
                           ↓
              PostgreSQL (:5432) + pgvector
              + Redis (:6379)
              + Tavily MCP (external, web-grounded RAG)
              + RxNorm API (external, drug normalization)
```

**Express.js responsibilities:**
- JWT token issuance and verification
- User registration and login
- RBAC role guards (dentist, orthopedist, admin)
- Audit logging middleware (all clinical actions)
- CORS configuration
- Rate limiting (per-user, per-endpoint)
- Proxying all `/api/*` requests to FastAPI with user context headers

**FastAPI responsibilities:**
- Patient CRUD and search
- Dental chart APIs (teeth, tooth events, procedures)
- Orthopedic chart APIs (body regions, bones, bone events)
- Drug concept resolution (RxNorm)
- Drug interaction checking
- RAG ingestion pipeline
- RAG retrieval via Tavily MCP (web-grounded) + local pgvector
- Patient AI assistant (chat endpoint)
- Citation validation
- Structured response formatting

---

## 5. Sub-Project Decomposition

| # | Sub-Project | Scope | Dependencies |
|---|------------|-------|---------------|
| SP-1 | Foundation | Project structure, Express gateway, FastAPI scaffold, PostgreSQL schema (patients table included), auth, RBAC, Redis, Docker Compose | None |
| SP-2 | Dental Module | Tooth model, numbering adapters (Universal/FDI/Palmer), interactive odontogram API, tooth events, dental chart frontend | SP-1 |
| SP-3 | Orthopedic Module | Body regions, bones, skeleton visualization API, bone events, skeleton frontend | SP-1 |
| SP-4 | Patient Module | Patient profiles, medical history, medications, allergies, appointments, audit logging, patient overview UI | SP-1 |
| SP-5 | Drug Intelligence | Drug provider interface, RxNorm integration, interaction model, drug interaction checker UI | SP-1 |
| SP-6 | RAG & AI | Tavily MCP integration, document ingestion, chunking, embeddings, hybrid retrieval, patient AI assistant, citation engine | SP-1 through SP-5 |

**Parallelization:** SP-2 and SP-3 can run in parallel (both depend only on SP-1).

**Build order:** SP-1 → SP-2 ∥ SP-3 → SP-4 → SP-5 → SP-6

---

## 6. Database Design

### 6.1 Core Tables (SP-1)

```sql
-- Users and auth
users (id UUID PK, email, password_hash, full_name, role, clinic_id, created_at, updated_at, deleted_at)
roles (id UUID PK, name, permissions JSONB)
clinics (id UUID PK, name, address, phone, created_at, updated_at)

-- Patients
patients (id UUID PK, clinic_id FK, first_name, last_name, date_of_birth, gender, phone, email, address, emergency_contact, created_at, updated_at, created_by, deleted_at)
patient_access (id UUID PK, patient_id FK, user_id FK, access_level, granted_at, granted_by)

-- Appointments
appointments (id UUID PK, patient_id FK, user_id FK, clinic_id FK, scheduled_at, duration_minutes, status, type, notes, created_at, updated_at)
```

### 6.2 Dental Tables (SP-2)

```sql
dental_charts (id UUID PK, patient_id FK, created_at, updated_at)
teeth (id UUID PK, dental_chart_id FK, tooth_number_canonical_fdi, tooth_name, dentition_type, created_at, updated_at)
tooth_events (id UUID PK, tooth_id FK, patient_id FK, event_type, procedure_name, diagnosis, date, status, surfaces JSONB, provider_id FK, notes, attachments JSONB, created_at, updated_at, created_by)
```

### 6.3 Orthopedic Tables (SP-3)

```sql
orthopedic_charts (id UUID PK, patient_id FK, created_at, updated_at)
body_regions (id UUID PK, orthopedic_chart_id FK, region_name, region_code, side, created_at, updated_at)
bones (id UUID PK, body_region_id FK, bone_name, bone_code, side, created_at, updated_at)
bone_events (id UUID PK, bone_id FK, patient_id FK, event_type, diagnosis, date, status, treatment, healing_status, side, notes, attachments JSONB, created_at, updated_at, created_by)
```

### 6.4 Patient Enrichment Tables (SP-4)

```sql
medical_histories (id UUID PK, patient_id FK, condition_name, diagnosed_date, status, notes, created_at, updated_at)
allergies (id UUID PK, patient_id FK, allergen, severity, reaction, noted_date, created_at, updated_at)
medications (id UUID PK, patient_id FK, drug_name, dosage, frequency, route, start_date, end_date, prescriber, status, created_at, updated_at)
```

### 6.5 Drug/RAG Tables (SP-5/SP-6)

```sql
drug_concepts (id UUID PK, rxnorm_cui, name, generic_name, drug_class, created_at)
drug_aliases (id UUID PK, drug_concept_id FK, alias, alias_type, created_at)
drug_interactions (id UUID PK, drug_a_id FK, drug_b_id FK, severity, mechanism, clinical_significance, evidence_source, evidence_strength, created_at)

knowledge_documents (id UUID PK, title, source, document_type, content_hash, metadata JSONB, created_at)
knowledge_chunks (id UUID PK, document_id FK, chunk_index, content, embedding vector(1536), metadata JSONB, created_at)
rag_citations (id UUID PK, query_id, chunk_id FK, claim_text, evidence_text, source, validated BOOLEAN, created_at)
```

### 6.6 Cross-Cutting Tables

```sql
audit_logs (id UUID PK, user_id FK, action, resource_type, resource_id, timestamp, success, metadata JSONB, ip_address)
attachments (id UUID PK, patient_id FK, entity_type, entity_id, file_name, file_path, file_type, file_size, uploaded_by FK, created_at)
medical_images (id UUID PK, patient_id FK, bone_id FK, image_type, file_path, description, taken_at, uploaded_by FK, created_at)
```

### 6.7 Index Strategy

```sql
-- High-traffic lookup indexes
CREATE INDEX idx_patients_clinic ON patients(clinic_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_patients_name ON patients(last_name, first_name) WHERE deleted_at IS NULL;
CREATE INDEX idx_tooth_events_tooth ON tooth_events(tooth_id, date DESC);
CREATE INDEX idx_tooth_events_patient ON tooth_events(patient_id, date DESC);
CREATE INDEX idx_bone_events_bone ON bone_events(bone_id, date DESC);
CREATE INDEX idx_bone_events_patient ON bone_events(patient_id, date DESC);
CREATE INDEX idx_appointments_patient ON appointments(patient_id, scheduled_at);
CREATE INDEX idx_appointments_user ON appointments(user_id, scheduled_at);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, timestamp DESC);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_drug_concepts_rxnorm ON drug_concepts(rxnorm_cui);
CREATE INDEX idx_drug_interactions_drugs ON drug_interactions(drug_a_id, drug_b_id);
CREATE INDEX idx_knowledge_chunks_embedding ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_medications_patient ON medications(patient_id) WHERE status = 'active';
```

---

## 7. API Design

### 7.1 Auth APIs (Express)

```
POST   /api/auth/register     — Register new user
POST   /api/auth/login        — Login, returns JWT
GET    /api/auth/me           — Current user profile
POST   /api/auth/logout       — Invalidate session
```

### 7.2 Patient APIs (FastAPI, proxied)

```
GET    /api/patients                    — List patients (search, filter)
POST   /api/patients                    — Create patient
GET    /api/patients/{patient_id}       — Get patient profile
PUT    /api/patients/{patient_id}       — Update patient
DELETE /api/patients/{patient_id}       — Soft delete patient
GET    /api/patients/{patient_id}/overview — Patient clinical summary
```

### 7.3 Dental APIs (FastAPI, proxied)

```
GET    /api/patients/{pid}/dental-chart           — Get dental chart
GET    /api/patients/{pid}/teeth/{tid}            — Get tooth details
GET    /api/patients/{pid}/teeth/{tid}/events     — Get tooth event history
POST   /api/patients/{pid}/teeth/{tid}/events     — Create tooth event
PUT    /api/patients/{pid}/teeth/{tid}/events/{eid} — Update tooth event
```

### 7.4 Orthopedic APIs (FastAPI, proxied)

```
GET    /api/patients/{pid}/skeleton                — Get skeleton with regions/bones
GET    /api/patients/{pid}/bones/{bid}             — Get bone details
GET    /api/patients/{pid}/bones/{bid}/events      — Get bone event history
POST   /api/patients/{pid}/bones/{bid}/events      — Create bone event
PUT    /api/patients/{pid}/bones/{bid}/events/{eid} — Update bone event
```

### 7.5 Drug APIs (FastAPI, proxied)

```
POST   /api/drugs/resolve                — Resolve drug name to canonical concept
POST   /api/drug-interactions/check      — Check interactions between 2+ drugs
GET    /api/drugs/search?q=              — Search drug concepts
```

### 7.6 AI Chat API (FastAPI, proxied)

```
POST   /api/chat/patient                 — Patient-scoped AI chat
Body:  { "patient_id": "...", "message": "..." }
Returns: Structured JSON with summary, findings, citations
```

### 7.7 Audit API (FastAPI, proxied)

```
GET    /api/audit-log                    — Query audit logs (admin only)
```

---

## 8. RAG Architecture (Tavily MCP + pgvector)

### 8.1 Knowledge Sources

| Source | Provider | Purpose |
|--------|----------|---------|
| Web-grounded clinical knowledge | **Tavily MCP** | Drug interactions, current clinical guidelines, evidence summaries |
| Patient records (scoped) | Local pgvector | Patient-specific retrieval for AI assistant |
| Drug concept metadata | RxNorm + cached | Drug normalization, canonical identifiers |

### 8.2 Ingestion Pipeline

```
Source Documents → Chunking (semantic, 512 tokens) → Metadata Enrichment
    → Embedding (local embedding model) → pgvector Storage
```

### 8.3 Hybrid Retrieval Pipeline

```
User Query
    ↓
Query Processing (intent detection, entity extraction)
    ↓
┌─────────────────────�──────────────────────┐
↓                     ↓                      ↓
Local Semantic        Tavily MCP            Metadata
(pgvector cosine)     (web-grounded)        Filtering
                      (clinical evidence)   (patient_id,
                                             doc_type,
                                             date range)
└─────────────────────┴──────────────────────┘
    ↓
Result Fusion (RRF — Reciprocal Rank Fusion)
    ↓
Reranking (cross-encoder or LLM-based)
    ↓
Top-K Context Selection
    ↓
Context Builder (prompt construction with citations)
    ↓
LLM Generation
    ↓
Citation Validation (verify claims match sources)
    ↓
Structured Response (Pydantic-validated JSON)
```

### 8.4 Tavily MCP Integration

- Tavily is invoked via MCP tool interface (`mcp__tavily__search`, `mcp__tavily__extract`)
- For drug interaction queries, search with topic filter `"general"` and `max_results` based on number of drugs
- Citations are constructed from `url` and `title` returned by Tavily
- When `TAVILY_API_KEY` is empty in `.env`, the RAG layer falls back to local pgvector only and returns "no external evidence available"

### 8.5 Patient-Scoped RAG

Every patient query enforces:
```
WHERE patient_id = <authenticated_patient_id>
```
This filter is applied at the database/vector level, NOT in the LLM prompt.

---

## 9. LLM Integration

### 9.1 Provider

Generation LLM is configurable via env (`LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`). Default placeholder: Tavily-augmented response generation. The LLM used for synthesis is separate from the Tavily retrieval API.

### 9.2 Structured Output Contract

All AI responses validated via Pydantic models:

```python
class PatientChatResponse(BaseModel):
    patient_name: str
    patient_id: str
    summary: str
    dental_history: list[dict]
    orthopedic_history: list[dict]
    recent_procedures: list[dict]
    current_medications: list[dict]
    allergies: list[dict]
    tooth_findings: list[dict]
    bone_findings: list[dict]
    important_notes: list[str]
    missing_information: list[str]
    citations: list[Citation]
```

### 9.3 Prompt Injection Defense

- Patient records treated as DATA, not instructions
- System prompt always has priority
- Retrieved documents wrapped in `<document>` tags with explicit "this is data" framing
- Tavily search results wrapped in `<evidence>` tags
- No user-controlled content injected into system instructions

---

## 10. Frontend Architecture

### 10.1 Page Structure

```
index.html
├── Role Selection Screen
├── Auth Screens (Login/Register)
├── Dashboard (role-adaptive)
├── Patient List
├── Patient Profile
│   ├── Overview Tab
│   ├── Dental Tab (Odontogram)
│   ├── Skeleton Tab
│   ├── Medical History Tab
│   ├── Medications Tab
│   ├── Appointments Tab
│   └── AI Assistant Tab
├── Drug Interaction Checker
├── Settings
└── Audit Log (admin)
```

### 10.2 Key Visual Components

**Interactive Odontogram (Dental Chart):**
- SVG-based anatomical tooth shapes (not a table)
- Universal Numbering (1-32 permanent, A-T primary) as primary; FDI/ISO + Palmer as adapters
- Color-coded tooth states (healthy, caries, restored, missing, extracted, implant, crown, root canal, fractured)
- Click to open tooth detail panel
- Add event without leaving chart

**Interactive Skeleton:**
- SVG-based anatomical skeleton
- Clickable body regions (head, neck, spine, shoulders, arms, hands, ribs, pelvis, hips, legs, feet)
- Color-coded states (white=normal, red=fracture, orange=under treatment, yellow=follow-up, green=healing, blue=surgical, gray=not assessed)
- Click to open bone detail panel
- Add event without leaving skeleton

**AI Chat Panel:**
- Structured card-based responses (not raw markdown)
- Patient context indicator
- Citation sources expandable (with Tavily URL links)
- Loading states

### 10.3 Design System

- CSS custom properties for all colors, spacing, typography
- Clinical-grade color palette (accessible contrast)
- Responsive (works on tablet and desktop)
- Consistent card-based layout
- Modal drawers for detail panels

---

## 11. Security Model

### 11.1 Authentication

- JWT tokens (short-lived, 15min access + 7-day refresh)
- bcrypt password hashing
- httpOnly cookies for token storage where possible

### 11.2 Authorization (RBAC)

| Role | Permissions |
|------|------------|
| dentist | patients.read, patients.write, dental.*.read, dental.*.write, drugs.read, chat.patient, appointments.* |
| orthopedist | patients.read, patients.write, ortho.*.read, ortho.*.write, drugs.read, chat.patient, appointments.* |
| admin | all permissions + audit.read + users.* |

### 11.3 Patient Isolation

- Every clinical query filtered by patient_id at the DB level
- Patient access table controls which users can see which patients
- API middleware verifies patient access before returning data
- Tested: Patient A cannot retrieve Patient B's information

### 11.4 Audit Logging

All security-sensitive actions logged:
```
LOGIN, LOGOUT, PATIENT_VIEW, PATIENT_SEARCH, PATIENT_UPDATE,
TOOTH_EVENT_CREATE, TOOTH_EVENT_UPDATE, BONE_EVENT_CREATE,
BONE_EVENT_UPDATE, DRUG_INTERACTION_QUERY, AI_QUERY, DOCUMENT_RETRIEVAL, ADMIN_ACTION
```

---

## 12. Clinical Safety

**This is a clinical information, visualization, documentation, and decision-support platform.**

It must NOT:
- Autonomously diagnose
- Prescribe medication
- Fabricate patient history, dental procedures, orthopedic history, or drug interactions
- Present unsupported clinical claims as facts

Language must use:
- "Based on the retrieved record..."
- "Evidence indicates..."
- "No supporting record was found..."
- "Insufficient evidence..."

---

## 13. Project Structure

```
clinical-platform/
├── frontend/
│   ├── index.html
│   ├── css/
│   ├── js/
│   └── assets/
├── backend/
│   ├── express/
│   │   ├── src/
│   │   │   ├── routes/
│   │   │   ├── middleware/
│   │   │   ├── services/
│   │   │   └── server.js
│   │   ├── package.json
│   │   └── Dockerfile
│   └── fastapi/
│       ├── app/
│       │   ├── api/
│       │   ├── models/
│       │   ├── schemas/
│       │   ├── services/
│       │   ├── rag/
│       │   ├── ai/
│       │   └── main.py
│       ├── requirements.txt
│       └── Dockerfile
├── database/
│   ├── migrations/
│   ├── seeds/
│   └── schema.sql
├── rag/
│   ├── ingestion/
│   ├── retrieval/
│   └── evaluation/
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── ERD.md
│   ├── API-SPEC.md
│   ├── RAG-ARCHITECTURE.md
│   ├── SECURITY.md
│   ├── DENTAL-DOMAIN.md
│   ├── ORTHOPEDIC-DOMAIN.md
│   └── USER-FLOWS.md
├── tests/
├── .env.example
├── docker-compose.yml
└── README.md
```

---

## 14. Acceptance Criteria

The project is complete when:

- [ ] Role selection screen works
- [ ] Dentist workspace loads with correct navigation
- [ ] Orthopedist workspace loads with correct navigation
- [ ] Authentication works (register, login, logout)
- [ ] RBAC enforces role-based access
- [ ] Patient CRUD works
- [ ] Patient isolation enforced (A can't see B)
- [ ] Interactive odontogram renders and is clickable
- [ ] Tooth events can be created and appear in history
- [ ] Tooth states update visually on the chart
- [ ] Interactive skeleton renders and is clickable
- [ ] Bone events can be created and appear in history
- [ ] Skeleton colors update based on clinical state
- [ ] Drug normalization works via RxNorm
- [ ] Drug interaction checker returns structured results
- [ ] RAG retrieval works with Tavily MCP + local pgvector hybrid
- [ ] Patient AI assistant returns structured, cited responses
- [ ] Citations include Tavily source URLs when used
- [ ] Audit logs record all clinical actions
- [ ] No secrets exposed in frontend code
- [ ] All API endpoints validate input
- [ ] Error responses are structured and user-friendly
- [ ] `docker compose up` brings up the full stack
