# Clinical Platform — Key Questions & Answers (问题解答文档)

## 1. Why Express + FastAPI Instead of a Single Backend?

**Decision**: Two backend services — Express (Node.js) as gateway, FastAPI (Python) as domain API.

**Rationale**:
- **Express** excels at JWT handling, static file serving, rate limiting, and middleware chains — all gateway concerns
- **FastAPI** excels at async Python operations (RxNorm API, Tavily API, sentence-transformers) — all domain concerns
- The proxy pattern means the browser only talks to one origin (`localhost:3000`), avoiding CORS issues
- Python has better ML/AI library support (sentence-transformers, pgvector, httpx async)

**Trade-off**:
| Factor | Single Express | Single FastAPI | Gateway + Domain |
|--------|---------------|----------------|-----------------|
| JWT handling | Good | Good | Express handles it |
| ML/AI libs | Poor (node-optional) | Excellent | FastAPI handles it |
| Static serving | Good | Fair | Express handles it |
| Complexity | Low | Low | Medium |
| Latency | N/A | N/A | +1 internal hop |

[VERIFY: clinical-platform/backend/express/src/server.js:20-29 — middleware chain]
[VERIFY: clinical-platform/backend/fastapi/app/main.py:1-32 — FastAPI app]

---

## 2. Why Header-Based Auth Context Instead of JWT Forwarding?

**Decision**: Express strips the JWT and injects `x-user-id`, `x-user-role`, `x-clinic-id` headers. FastAPI never sees JWTs.

**Rationale**:
- **Security**: FastAPI runs on an internal network only. Headers are simpler to validate than JWTs.
- **Separation of concerns**: FastAPI doesn't need to know about JWT signing, expiry, or refresh logic.
- **Simplicity**: FastAPI endpoints just read headers — no JWT library needed.
- **Trust boundary**: Express is the authentication authority. FastAPI trusts the gateway.

**Alternative considered**: Forward JWT to FastAPI and re-verify there.
- Rejected because: duplicate JWT_SECRET management, unnecessary crypto overhead, tighter coupling.

[VERIFY: clinical-platform/backend/express/src/routes/proxy.js:15-20]
[VERIFY: clinical-platform/backend/fastapi/app/services/auth_context.py:11-22]

---

## 3. Why Lazy Chart Initialization?

**Decision**: Dental and orthopedic charts are created on first access, not when a patient is created.

**Rationale**:
- Not every patient needs a dental chart (orthopedic-only patients)
- Not every patient needs a skeleton chart (dental-only patients)
- Lazy init avoids creating 32 teeth + 26 regions + 17 bones per patient upfront
- The `_ensure_chart()` / `_ensure_skeleton()` pattern is idempotent — safe to call repeatedly

**Trade-off**: First access has slightly higher latency (~30ms for INSERT 32 rows). Subsequent accesses are fast.

[VERIFY: clinical-platform/backend/fastapi/app/api/dental.py:71-98]
[VERIFY: clinical-platform/backend/fastapi/app/api/orthopedic.py:125-162]

---

## 4. Why Reciprocal Rank Fusion for RAG?

**Decision**: Use RRF (k=60) to merge local pgvector results with Tavily web results.

**Rationale**:
- Local results: cosine similarity scores (0-1 range, different scales per query)
- Tavily results: their own relevance scores (different scale)
- RRF normalizes both by rank position, avoiding scale mismatch
- RRF is parameter-free (k=60 is standard) — no tuning needed
- Documents appearing in both result sets get naturally boosted

**Alternative considered**: Weighted score averaging.
- Rejected because: requires tuning weights per query type, scale mismatch between cosine and Tavily scores.

**RRF formula**: `score(d) = Σ 1/(k + rank_i(d) + 1)` where k=60

[VERIFY: clinical-platform/backend/fastapi/app/rag/retrieval.py:62-77]

---

## 5. Why Hash-Based Embedding Fallback?

**Decision**: When sentence-transformers can't load, use a deterministic hash-based pseudo-embedding.

**Rationale**:
- The demo should run without GPU or heavy ML packages
- Hash embedding is deterministic (same text → same vector) — good for consistency
- It's NOT semantically meaningful (different meanings can hash similarly)
- The local search will still return results (just less meaningful ones)
- Tavily web search compensates with real semantic results

**Trade-off**: Local search quality degrades significantly with hash embedding. The system still functions because RRF combines with Tavily results.

[VERIFY: clinical-platform/backend/fastapi/app/rag/embeddings.py:14-21 — _hash_embed()]
[VERIFY: clinical-platform/backend/fastapi/app/rag/embeddings.py:41-54 — embed_text() with fallback]

---

## 6. Why Soft Delete for Users and Patients?

**Decision**: Use `deleted_at` timestamp column instead of physical DELETE.

**Rationale**:
- **Data integrity**: References from other tables (appointments, audit_logs) remain valid
- **Compliance**: Medical records often require audit trails — soft delete preserves history
- **Recovery**: Accidental deletes can be reversed by setting `deleted_at = NULL`
- **Query pattern**: All queries include `WHERE deleted_at IS NULL` — consistent filter

**Trade-off**: Slightly more complex queries, index bloat over time. Partial indexes (`WHERE deleted_at IS NULL`) mitigate this.

[VERIFY: clinical-platform/database/schema.sql:33 — users.deleted_at]
[VERIFY: clinical-platform/database/schema.sql:51 — patients.deleted_at]
[VERIFY: clinical-platform/database/schema.sql:108-111 — partial indexes]

---

## 7. Why Rule-Based AI Synthesis Instead of LLM?

**Decision**: The `PatientAssistant.chat()` method uses rule-based string concatenation, not an LLM.

**Rationale**:
- **No API key dependency**: Works offline, no OpenAI/Claude costs
- **Clinical safety**: Rule-based output is predictable and auditable
- **Demo simplicity**: No LLM rate limits, latency, or cost
- **Future-proof**: The `PatientAssistant` class is designed to be extended with LLM synthesis later

**Current limitation**: The summary is a flat concatenation of facts, not a natural language response. The `context` parameter in `ChatRequest` is accepted but not used.

[VERIFY: clinical-platform/backend/fastapi/app/ai/patient_assistant.py:115-128 — synthesis]
[VERIFY: clinical-platform/backend/fastapi/app/ai/patient_assistant.py:6-7 — clinical safety note]

---

## 8. How Does Clinic-Level Data Isolation Work?

**Decision**: Every FastAPI endpoint checks `user.clinic_id` against the patient's `clinic_id`.

**Pattern**:
```python
if user.clinic_id and p["clinic_id"] != user.clinic_id:
    raise HTTPException(status_code=403, ...)
```

**Rationale**:
- Simple, explicit check at every endpoint
- No complex SQL JOIN through `patient_access` table
- `clinic_id` is injected by Express proxy — cannot be forged by client
- Admin users with `clinic_id = None` can access all clinics (future use)

**Gap**: The `patient_access` table exists in the schema but is **not enforced** in FastAPI routes. It's only populated in seed data.

[VERIFY: clinical-platform/backend/fastapi/app/api/patients.py:62-63]
[VERIFY: clinical-platform/backend/fastapi/app/api/dental.py:114-115]
[VERIFY: clinical-platform/backend/fastapi/app/api/orthopedic.py:177-178]
[VERIFY: clinical-platform/database/schema.sql:55-63 — patient_access table]

---

## 9. Why pgvector with ivfflat Instead of HNSW?

**Decision**: Use `ivfflat` index for vector similarity search.

**Rationale**:
- ivfflat is simpler to build and understand
- For the demo dataset (small number of knowledge_chunks), ivfflat performs well
- HNSW is better for large-scale production (millions of vectors)
- `lists = 100` is a reasonable default for <100k vectors

**Production recommendation**: Switch to HNSW for larger datasets:
```sql
CREATE INDEX idx_knowledge_chunks_embedding
    ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);
```

[VERIFY: clinical-platform/database/migrations/006_rag.sql:44 — ivfflat index]

---

## 10. Why Vanilla JS Instead of React/Vue?

**Decision**: Frontend uses vanilla JavaScript with ES modules, no framework.

**Rationale**:
- **Simplicity**: No build step, no node_modules, no bundler
- **Directness**: DOM manipulation is straightforward for the UI complexity
- **Portability**: Works in any browser with ES module support
- **Demo focus**: The platform's value is in the backend (dental/orthopedic/RAG), not the frontend framework

**Trade-off**: Component reusability is limited. The `Odontogram` and `SkeletonSVG` components are custom-built and would need rewriting for a framework migration.

[VERIFY: clinical-platform/frontend/js/app.js:1-33 — SPA with vanilla JS]
[VERIFY: clinical-platform/frontend/index.html:1-15 — no framework script tags]

---

## 11. How Are Drug Interactions Seeded?

**Decision**: The `drug_interactions` table is pre-seeded via `database/seeds/drug_interactions.sql`.

**Flow**:
1. Drug names are resolved to RxNorm CUIs via `RxNormProvider`
2. Resolved concepts are upserted into `drug_concepts`
3. Interaction pairs are looked up from pre-seeded `drug_interactions`
4. The `CHECK (drug_a_id < drug_b_id)` constraint ensures canonical ordering

**Gap**: The seed file `drug_interactions.sql` exists but its content is not shown in the codebase. The interaction check only works for pre-seeded pairs — it cannot discover new interactions at runtime.

[VERIFY: clinical-platform/database/seeds/drug_interactions.sql — seed file exists]
[VERIFY: clinical-platform/database/migrations/005_drugs.sql:31 — CHECK constraint]

---

## 12. What Happens When Tavily API Key Is Missing?

**Decision**: The system degrades gracefully — local search still works, Tavily returns empty.

**Flow**:
1. `TavilyClient.__init__()` (tavily.py:25-28): `self.enabled = bool(self.api_key) and self.api_key != "your-tavily-api-key"`
2. `TavilyClient.search()` (tavily.py:30-31): `if not self.enabled: return []`
3. `HybridRetriever.retrieve()` (retrieval.py:59-60): Local results only, Tavily returns `[]`
4. RRF fusion still works — local results get scores, Tavily results are empty
5. `PatientAssistant.chat()` (patient_assistant.py:135-137): Adds warning "No supporting external evidence was retrieved"

[VERIFY: clinical-platform/backend/fastapi/app/rag/tavily.py:25-28, 30-31]
[VERIFY: clinical-platform/backend/fastapi/app/ai/patient_assistant.py:135-139]

---

## 13. Security Considerations & Gaps

### Implemented
- ✅ JWT authentication with short expiry (15min)
- ✅ bcrypt password hashing (cost 12)
- ✅ Rate limiting (100 req/15min)
- ✅ CORS properly configured
- ✅ Helmet security headers
- ✅ Audit logging of all API requests
- ✅ Clinic-level data isolation
- ✅ Soft delete with partial indexes
- ✅ SQL parameterized queries (no injection)

### Gaps / Future Work
- ⚠️ `requireRole()` middleware exists but is **not wired** to any route
- ⚠️ `patient_access` table exists but is **not enforced** in FastAPI
- ⚠️ Redis is declared in docker-compose but **not used** anywhere
- ⚠️ Refresh token rotation not implemented (no token revocation)
- ⚠️ No HTTPS in development (production would need TLS termination)
- ⚠️ JWT_SECRET defaults to `'dev-secret'` — must be overridden
- ⚠️ CORS `allow_origins=["*"]` — should be restricted in production

[VERIFY: clinical-platform/backend/express/src/middleware/rbac.js:1-12 — exists but unused]
[VERIFY: clinical-platform/backend/fastapi/app/main.py:11-17 — CORS allow_origins=["*"]]
[VERIFY: clinical-platform/docker-compose.yml:21-29 — Redis declared]
