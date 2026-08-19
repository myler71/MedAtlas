# Clinical Platform — Key Functions Analysis (关键函数分析)

## 1. Authentication & Authorization Functions

### 1.1 `authenticate(req, res, next)` — JWT Verification Middleware

[VERIFY: clinical-platform/backend/express/src/middleware/auth.js:6-18]

```javascript
export function authenticate(req, res, next) {
  const token = req.cookies?.token || req.headers.authorization?.replace('Bearer ', '');
  if (!token) {
    return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'No token provided' } });
  }
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.user = decoded;
    next();
  } catch (err) {
    return res.status(401).json({ error: { code: 'INVALID_TOKEN', message: 'Invalid or expired token' } });
  }
}
```

**Line-by-line analysis**:
- **Line 7**: Extracts token from two sources: httpOnly cookie (`req.cookies?.token`) OR `Authorization: Bearer <token>` header. Cookie takes priority.
- **Line 8-9**: Returns 401 with structured error if no token found.
- **Line 11**: `jwt.verify()` validates signature + expiry. Throws `TokenExpiredError` or `JsonWebTokenError`.
- **Line 12**: Decoded payload becomes `req.user` — contains `{ id, email, role, clinic_id }` (from generateToken).
- **Line 13**: Calls `next()` to pass control to next middleware/route.

**Security notes**:
- JWT_SECRET defaults to `'dev-secret'` — must be overridden in production via env var
- Token is extracted from httpOnly cookie (XSS-resistant) or header (for API clients)

### 1.2 `generateToken(user)` — Access Token Creation

[VERIFY: clinical-platform/backend/express/src/middleware/auth.js:20-26]

```javascript
export function generateToken(user) {
  return jwt.sign(
    { id: user.id, email: user.email, role: user.role, clinic_id: user.clinic_id },
    JWT_SECRET,
    { expiresIn: `${process.env.JWT_EXPIRY_MINUTES || 15}m` }
  );
}
```

**Payload structure**: `{ id: UUID, email: string, role: string, clinic_id: UUID|null }`
**Expiry**: 15 minutes (configurable via `JWT_EXPIRY_MINUTES` env)

### 1.3 `requireRole(...roles)` — RBAC Middleware Factory

[VERIFY: clinical-platform/backend/express/src/middleware/rbac.js:1-12]

```javascript
export function requireRole(...roles) {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'Not authenticated' } });
    }
    if (!roles.includes(req.user.role)) {
      return res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Insufficient permissions' } });
    }
    next();
  };
}
```

**Usage pattern**: `router.get('/admin', requireRole('admin'), handler)`
**Note**: This middleware exists but is **not currently wired** to any route in the codebase. Authorization is handled at the FastAPI layer via clinic_id checks instead.

---

## 2. Proxy & Auth Context Functions

### 2.1 `createProxyRouter(fastapiBase)` — API Proxy with Auth Injection

[VERIFY: clinical-platform/backend/express/src/routes/proxy.js:6-25]

```javascript
export function createProxyRouter(fastapiBase) {
  const router = Router();
  router.use(authenticate);
  router.use('/', createProxyMiddleware({
    target: fastapiBase,
    changeOrigin: true,
    pathRewrite: (path) => path,  // keep the /api/* prefix
    onProxyReq: (proxyReq, req) => {
      if (req.user) {
        proxyReq.setHeader('x-user-id', req.user.id);
        proxyReq.setHeader('x-user-role', req.user.role);
        proxyReq.setHeader('x-clinic-id', req.user.clinic_id || '');
      }
    }
  }));
  return router;
}
```

**Key design**: Express acts as a trust boundary. After JWT verification, it strips the token and injects simplified headers that FastAPI can trust without JWT validation.

**Header mapping**:
| Header | Source | Type |
|--------|--------|------|
| `x-user-id` | `req.user.id` | UUID string |
| `x-user-role` | `req.user.role` | "dentist" \| "orthopedist" \| "admin" |
| `x-clinic-id` | `req.user.clinic_id` | UUID string or "" |

### 2.2 `get_user_context()` — FastAPI Auth Extraction

[VERIFY: clinical-platform/backend/fastapi/app/services/auth_context.py:11-22]

```python
def get_user_context(
    x_user_id: Optional[str] = Header(None),
    x_user_role: Optional[str] = Header(None),
    x_clinic_id: Optional[str] = Header(None),
) -> UserContext:
    if not x_user_id or not x_user_role:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Missing auth context"})
    try:
        clinic_id = UUID(x_clinic_id) if x_clinic_id else None
        return UserContext(user_id=UUID(x_user_id), role=x_user_role, clinic_id=clinic_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"code": "INVALID_CONTEXT", "message": "Invalid user context"})
```

**Error handling**:
- Missing headers → 401 UNAUTHORIZED
- Invalid UUID format → 400 INVALID_CONTEXT
- `clinic_id` can be None (for admin users not scoped to a clinic)

---

## 3. Dental Domain Functions

### 3.1 `_ensure_chart(db, patient_id)` — Lazy Dental Chart Initialization

[VERIFY: clinical-platform/backend/fastapi/app/api/dental.py:71-98]

```python
def _ensure_chart(db: Session, patient_id: UUID) -> UUID:
    row = db.execute(
        text("SELECT id FROM dental_charts WHERE patient_id = :pid"),
        {"pid": str(patient_id)},
    ).mappings().first()
    if row:
        return row["id"]
    chart_row = db.execute(
        text("INSERT INTO dental_charts (patient_id) VALUES (:pid) RETURNING id"),
        {"pid": str(patient_id)},
    ).mappings().first()
    chart_id = chart_row["id"]
    for fdi in all_permanent_fdi():
        db.execute(
            text("""INSERT INTO teeth (dental_chart_id, tooth_number_fdi, dentition_type,
                    position_in_quadrant, quadrant, tooth_name)
                    VALUES (:cid, :fdi, 'permanent', :pos, :quad, :name)"""),
            {
                "cid": str(chart_id),
                "fdi": fdi,
                "pos": fdi % 10,
                "quad": fdi // 10,
                "name": f"Tooth {fdi}",
            },
        )
    db.commit()
    return chart_id
```

**Algorithm**:
1. Check if chart exists → return existing chart_id
2. Create chart → get new chart_id
3. Seed 32 permanent teeth using FDI numbering:
   - For each FDI in `all_permanent_fdi()` (11-18, 21-28, 31-38, 41-48):
     - `position_in_quadrant = fdi % 10`
     - `quadrant = fdi // 10`
4. Commit and return chart_id

**Performance**: First call creates 32 tooth rows in one transaction. Subsequent calls are O(1) SELECT.

### 3.2 `_derive_state(event_type)` — Tooth State Derivation

[VERIFY: clinical-platform/backend/fastapi/app/api/dental.py:56-68]

```python
def _derive_state(event_type: Optional[str]) -> str:
    if not event_type:
        return "healthy"
    mapping = {
        "caries": "caries",
        "restoration": "restored",
        "extraction": "missing",
        "root_canal": "root_canal",
        "crown": "crown",
        "implant": "implant",
        "fracture": "fractured",
    }
    return mapping.get(event_type, "treated")
```

**State mapping**:
| event_type | Visual State | CSS Class |
|-----------|-------------|-----------|
| (null) | healthy | tooth-state-healthy |
| caries | caries | tooth-state-caries |
| restoration | restored | tooth-state-restored |
| extraction | missing | tooth-state-missing |
| root_canal | root_canal | tooth-state-root_canal |
| crown | crown | tooth-state-crown |
| implant | implant | tooth-state-implant |
| fracture | fractured | tooth-state-fractured |
| (other) | treated | tooth-state-restored |

### 3.3 `fdi_to_universal(fdi)` — Tooth Numbering Conversion

[VERIFY: clinical-platform/backend/fastapi/app/services/dental/numbering.py:35-58]

```python
def fdi_to_universal(fdi: int) -> Optional[str]:
    if fdi < 11 or fdi > 85:
        return None
    fdi_quadrant = fdi // 10
    position = fdi % 10
    if fdi_quadrant in (1, 2, 3, 4):
        if not (1 <= position <= 8):
            return None
        base = (fdi_quadrant - 1) * 8
        universal_num = base + position
        return str(universal_num)
    elif fdi_quadrant in (5, 6, 7, 8):
        if not (1 <= position <= 5):
            return None
        idx = (fdi_quadrant - 5) * 5 + (position - 1)
        return chr(ord("A") + idx)
    return None
```

**Permanent teeth formula**: `universal = (fdi_quadrant - 1) * 8 + position`
- FDI 11 → (1-1)*8 + 1 = 1 (UR central incisor)
- FDI 48 → (4-1)*8 + 8 = 32 (LR third molar)

**Primary teeth formula**: `letter = chr(A + (fdi_quadrant - 5) * 5 + (position - 1))`
- FDI 51 → A (UR primary central incisor)
- FDI 85 → T (LR primary second molar)

---

## 4. Orthopedic Domain Functions

### 4.1 `_ensure_skeleton(db, patient_id)` — Lazy Skeleton Initialization

[VERIFY: clinical-platform/backend/fastapi/app/api/orthopedic.py:125-162]

Creates:
- 1 `orthopedic_charts` row
- 26 `body_regions` rows (from `STANDARD_BODY_REGIONS`)
- 17 `bones` rows (from `BONES_PER_REGION` — not all regions have bones)

**Region-to-bone mapping** (orthopedic.py:46-64):
- 11 regions have defined bones (head, cervical, thoracic, lumbar, sacrum, ribs, pelvis, shoulder, upper_arm, elbow, lower_arm, hand, hip, upper_leg, knee, lower_leg, foot)
- Regions without explicit bones (e.g., shoulder bilateral) inherit from the region's bone list

### 4.2 `_derive_bone_state(event_type)` — Bone State Derivation

[VERIFY: clinical-platform/backend/fastapi/app/api/orthopedic.py:109-122]

| event_type | Visual State |
|-----------|-------------|
| (null) | normal |
| fracture | fracture |
| sprain | under_treatment |
| dislocation | under_treatment |
| surgery | surgical |
| implant | surgical |
| arthritis | chronic |
| healing | healing |
| follow_up | follow_up |
| (other) | treated |

### 4.3 `SkeletonSVG._worstState(states)` — Severity Aggregation

[VERIFY: clinical-platform/frontend/js/components/skeleton-svg.js:64-68]

```javascript
_worstState(states) {
    const priority = ['fracture', 'surgical', 'under_treatment', 'follow_up', 'chronic', 'healing', 'treated', 'normal'];
    for (const p of priority) if (states.includes(p)) return p;
    return 'normal';
}
```

**Algorithm**: Linear scan through severity-ordered priority list. First match wins. Used to color body regions in the SVG — a region with any fracture shows as "fracture" regardless of other bones' states.

---

## 5. Drug Intelligence Functions

### 5.1 `RxNormProvider.resolve(name_or_cui)` — Drug Resolution

[VERIFY: clinical-platform/backend/fastapi/app/services/drugs/rxnorm.py:43-84]

```
Input: "Aspirin" (or "1191" CUI)
  │
  ├─ Not numeric? → search("Aspirin", limit=1)
  │   └─ GET /REST/approximateTerm.json?term=Aspirin&maxEntries=1
  │       → candidates[0].rxcui → recursive resolve(cui)
  │
  ├─ GET /REST/rxcui/{cui}/property.json?propName=RxNorm Name
  │   → name from propConceptGroup
  │
  ├─ GET /REST/rxcui/{cui}/related.json?tty=IN+MIN+BN
  │   → conceptGroups:
  │       tty="VA" → drug_class (first concept name)
  │       All groups → aliases (ingredients + brand names)
  │
  └─ Return DrugConcept{rxnorm_cui, name, drug_class, aliases[:20]}
```

**External API**: RxNorm REST at `https://rxnav.nlm.nih.gov/REST`
**Timeout**: 10 seconds per request

### 5.2 `DrugInteractionService.check()` — Interaction Checking

[VERIFY: clinical-platform/backend/fastapi/app/services/drugs/interactions.py:37-98]

**Algorithm** (O(n²) pairwise check):
1. Resolve each drug name → canonical CUI (with upsert into `drug_concepts` + `drug_aliases`)
2. For each pair (i, j) where i < j:
   - Sort CUIs: `a, b = sorted([cuis[i], cuis[j]])`
   - Query `drug_interactions` table (pre-seeded data)
3. Collect warnings for unresolved drugs
4. Return `InteractionCheckResult`

**DB constraint**: `CHECK (drug_a_id < drug_b_id)` ensures canonical ordering — each pair stored exactly once.

---

## 6. RAG Pipeline Functions

### 6.1 `embed_text(text)` — Text Embedding with Fallback

[VERIFY: clinical-platform/backend/fastapi/app/rag/embeddings.py:41-54]

```python
def embed_text(text: str) -> List[float]:
    model = _try_load_model()
    if model is not None:
        try:
            vec = model.encode(text).tolist()
            if len(vec) < _DIM:
                vec = vec + [0.0] * (_DIM - len(vec))
            else:
                vec = vec[:_DIM]
            return vec
        except Exception:
            pass
    return _hash_embed(text)
```

**Primary**: `SentenceTransformer("all-MiniLM-L6-v2")` → 384-dim → padded to 1536
**Fallback**: `_hash_embed()` → deterministic pseudo-embedding (SHA256-based)

**Hash embedding algorithm** (`_hash_embed`, embeddings.py:14-21):
1. Initialize 1536-dim zero vector
2. For each word (up to 1536):
   - Compute SHA256 of word
   - Take first 8 hex chars → integer hash
   - Place `1/(1 + i*0.01)` at position `(i + hash) % 1536`
3. L2-normalize the vector

**Limitation**: Hash embedding is NOT semantically meaningful. It's only for demo purposes when ML deps are unavailable.

### 6.2 `HybridRetriever._local_search()` — pgvector Similarity Search

[VERIFY: clinical-platform/backend/fastapi/app/rag/retrieval.py:23-43]

```python
def _local_search(self, db, query, patient_id, top_k=5):
    emb = embed_text(query)
    emb_str = "[" + ",".join(f"{x:.6f}" for x in emb) + "]"
    sql = """SELECT id, content, metadata,
                    1 - (embedding <=> CAST(:emb AS vector)) AS similarity
             FROM knowledge_chunks WHERE embedding IS NOT NULL"""
    if patient_id:
        sql += " AND (metadata->>'patient_id' = :pid
                  OR document_id IN (
                    SELECT id FROM knowledge_documents
                    WHERE document_type = 'patient_record'
                      AND metadata->>'patient_id' = :pid))"
    sql += " ORDER BY embedding <=> CAST(:emb AS vector) LIMIT :k"
```

**Distance metric**: Cosine distance via pgvector `<=>` operator
**Score**: `similarity = 1 - cosine_distance` (range 0-1, higher = more similar)
**Patient scoping**: Filters by `metadata->>'patient_id'` OR document type = 'patient_record'

### 6.3 `HybridRetriever.retrieve()` — RRF Fusion

[VERIFY: clinical-platform/backend/fastapi/app/rag/retrieval.py:52-78]

```python
async def retrieve(self, db, query, patient_id=None, top_k=5):
    local_results = self._local_search(db, query, patient_id, top_k=top_k)
    tavily_results = await self._tavily_search(query, max_results=top_k)

    k = 60  # RRF constant
    scores = {}
    chunks = {}

    for rank, chunk in enumerate(local_results):
        key = f"local:{chunk.content[:80]}"
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        chunks[key] = chunk

    for rank, chunk in enumerate(tavily_results):
        key = f"tavily:{chunk.content[:80]}"
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        chunks[key] = chunk

    fused = sorted(chunks.values(), key=lambda c: scores.get(...), reverse=True)
    return fused[:top_k]
```

**RRF Formula**: `score(d) = Σ_i 1/(k + rank_i(d) + 1)` where k=60
**Deduplication**: Content prefix (first 80 chars) used as key. Same content from both sources gets summed score.

---

## 7. Frontend Component Functions

### 7.1 `Odontogram.render()` — Tooth SVG Grid

[VERIFY: clinical-platform/frontend/js/components/odontogram.js:31-58]

```
Algorithm:
1. Group teeth by quadrant: {1: [], 2: [], 3: [], 4: []}
2. Create 2 rows:
   - Upper: Q1 (UR) + Q2 (UL)
   - Lower: Q3 (LL) + Q4 (LR)
3. For each row, render teeth sorted by position_in_quadrant DESC
4. Each tooth: SVG with path + state CSS class + label
5. Attach click handlers → onSelectTooth(tooth)
```

### 7.2 `SkeletonSVG._worstState()` — Region Color Selection

[VERIFY: clinical-platform/frontend/js/components/skeleton-svg.js:64-68]

```javascript
_worstState(states) {
    const priority = ['fracture', 'surgical', 'under_treatment', 'follow_up',
                      'chronic', 'healing', 'treated', 'normal'];
    for (const p of priority) if (states.includes(p)) return p;
    return 'normal';
}
```

**Purpose**: When a body region contains multiple bones with different states, the most severe state determines the region's color in the SVG.

---

## 8. Database Functions

### 8.1 `auditMiddleware(req, res, next)` — Request Audit Logger

[VERIFY: clinical-platform/backend/express/src/middleware/audit.js:6-30]

```javascript
export function auditMiddleware(req, res, next) {
  const start = Date.now();
  res.on('finish', async () => {
    const duration = Date.now() - start;
    if (!req.path.startsWith('/api/')) return;
    try {
      await pool.query(
        `INSERT INTO audit_logs (user_id, action, resource_type, resource_id,
         success, ip_address, metadata)
         VALUES ($1, $2, $3, $4, $5, $6, $7)`,
        [
          req.user?.id || null,
          `${req.method} ${req.path}`,
          req.path.split('/')[2] || null,
          req.params?.id || null,
          res.statusCode < 400,
          req.ip,
          JSON.stringify({ duration_ms: duration, status: res.statusCode })
        ],
      );
    } catch (e) {
      console.error('audit log fail', e);
    }
  });
  next();
}
```

**Key behavior**:
- Fires on `res.finish` event (after response sent) — non-blocking
- Only logs `/api/*` paths
- `resource_type` extracted from URL path segment [2] (e.g., `/api/patients/123` → "patients")
- Errors logged but not propagated (audit failure doesn't break the request)

---

## 9. Function Call Graph (函数调用图)

```
server.js
├── helmet()
├── cors()
├── rateLimit()
├── auditMiddleware() ←── audit.js
│   └── pool.query() ←── db.js
├── authRouter ←── auth.js
│   ├── POST /register
│   │   ├── bcrypt.hash()
│   │   ├── pool.query() (INSERT)
│   │   ├── generateToken() ←── middleware/auth.js
│   │   └── generateRefreshToken()
│   ├── POST /login
│   │   ├── pool.query() (SELECT)
│   │   ├── bcrypt.compare()
│   │   ├── generateToken()
│   │   └── generateRefreshToken()
│   ├── GET /me ←── authenticate middleware
│   └── POST /logout
├── createProxyRouter() ←── proxy.js
│   ├── authenticate middleware
│   └── createProxyMiddleware()
│       └── onProxyReq: inject x-user-* headers
├── express.static(frontendPath)
└── errorHandler()

FastAPI main.py
├── patients.router ←── patients.py
│   ├── list_patients() → get_user_context() → SQL
│   ├── create_patient() → get_user_context() → SQL INSERT
│   ├── get_patient() → get_user_context() → SQL
│   ├── update_patient() → get_user_context() → SQL UPDATE
│   └── delete_patient() → get_user_context() → SQL (soft delete)
├── dental.router ←── dental.py
│   ├── get_dental_chart() → _ensure_chart() → numbering.fdi_to_*()
│   ├── list_tooth_events()
│   ├── create_tooth_event()
│   └── update_tooth_event()
├── orthopedic.router ←── orthopedic.py
│   ├── get_skeleton() → _ensure_skeleton()
│   ├── list_bone_events()
│   ├── create_bone_event()
│   └── update_bone_event()
├── drugs.router ←── drugs.py
│   ├── resolve_drug() → RxNormProvider.resolve()
│   ├── search_drugs() → RxNormProvider.search()
│   └── check_interactions() → DrugInteractionService.check()
├── chat.router ←── chat.py
│   └── chat_with_patient_assistant()
│       └── PatientAssistant.chat()
│           ├── _gather_patient_context() → 6 SQL queries
│           ├── HybridRetriever.retrieve()
│           │   ├── _local_search() → embed_text() → pgvector
│           │   ├── _tavily_search() → Tavily API
│           │   └── RRF fusion
│           └── Synthesize PatientChatResponse
├── appointments.router
├── patient_history.router
└── patient_overview.router
```
