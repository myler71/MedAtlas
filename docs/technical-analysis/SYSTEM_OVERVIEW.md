# Clinical Platform — System Overview (系统概述)

## 1. Project Identity (项目标识)

**Name**: Clinical Platform
**Type**: Full-stack medical information & documentation platform
**Domain**: Dental + Orthopedics + Pharmaceutical RAG
**Stack**: Express.js (gateway) → FastAPI (domain APIs) → PostgreSQL 16 + pgvector → Vanilla JS frontend

[VERIFY: clinical-platform/README.md:3 — "Dental + Orthopedics + Pharmaceutical RAG Clinical Information & Documentation Platform."]

---

## 2. Architecture Overview (架构总览)

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Browser                           │
│   index.html  →  app.js (SPA router)  →  api.js (fetch)        │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP :3000
┌───────────────────────────▼─────────────────────────────────────┐
│                     Express Gateway (Node.js)                   │
│  ┌──────────┐ ┌────────┐ ┌───────┐ ┌───────────┐ ┌──────────┐│
│  │   Auth   │ │  RBAC  │ │ Audit │ │  Rate     │ │  Error   ││
│  │ (JWT)    │ │        │ │       │ │  Limiter  │ │ Handler  ││
│  └──────────┘ └────────┘ └───────┘ └───────────┘ └──────────┘│
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           Proxy (/api/* → FastAPI :8000)                 │  │
│  │     Injects x-user-id, x-user-role, x-clinic-id headers │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Static File Server (frontend/)              │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP :8000 (internal)
┌───────────────────────────▼─────────────────────────────────────┐
│                    FastAPI Backend (Python)                      │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌────────────────┐  │
│  │ Patients │ │ Dental   │ │Orthopedic  │ │ Appointments   │  │
│  │ API      │ │ Chart    │ │ Skeleton   │ │                │  │
│  └──────────┘ └──────────┘ └────────────┘ └────────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌────────────────┐  │
│  │ Drugs    │ │ Patient  │ │ Patient    │ │ Chat (AI)      │  │
│  │ API      │ │ History  │ │ Overview   │ │                │  │
│  └──────────┘ └──────────┘ └────────────┘ └────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              RAG Pipeline                                │  │
│  │  HybridRetriever = pgvector(local) + Tavily(web) + RRF  │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│              PostgreSQL 16 + pgvector (Docker)                  │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌────────────────┐  │
│  │  Core    │ │ Dental   │ │Orthopedic  │ │ Enrichment     │  │
│  │  Tables  │ │ Tables   │ │ Tables     │ │ Tables         │  │
│  └──────────┘ └──────────┘ └────────────┘ └────────────────┘  │
│  ┌──────────┐ ┌──────────────────────────────────────────────┐ │
│  │  Drug    │ │  RAG (knowledge_documents, knowledge_chunks, │ │
│  │  Tables  │ │   rag_citations, rag_queries)                │ │
│  └──────────┘ └──────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Redis 7 (session cache — declared but not yet wired)    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

[VERIFY: clinical-platform/docker-compose.yml:1-57 — All four services: postgres, redis, express, fastapi]
[VERIFY: clinical-platform/backend/express/src/server.js:1-46 — Express gateway setup]
[VERIFY: clinical-platform/backend/fastapi/app/main.py:1-32 — FastAPI app with 8 routers]

---

## 3. Service Inventory (服务清单)

| Service | Technology | Port | Role | Entry Point |
|---------|-----------|------|------|-------------|
| **postgres** | pgvector/pgvector:pg16 | 5432 | Database | `database/schema.sql` |
| **redis** | redis:7-alpine | 6379 | Cache (unused) | — |
| **express** | Node.js + Express | 3000 | API gateway, auth, static server | `backend/express/src/server.js` |
| **fastapi** | Python + FastAPI | 8000 | Domain APIs, RAG, AI | `backend/fastapi/app/main.py` |

[VERIFY: clinical-platform/docker-compose.yml:3-56 — All service definitions]

---

## 4. Module Map (模块地图)

### 4.1 Express Gateway Modules

```
backend/express/src/
├── server.js              # App bootstrap, middleware chain, routes
├── routes/
│   ├── auth.js            # POST /register, /login, GET /me, POST /logout
│   └── proxy.js           # /api/* → FastAPI proxy with auth header injection
├── middleware/
│   ├── auth.js            # JWT verify, generateToken, generateRefreshToken
│   ├── rbac.js            # requireRole(...roles) middleware
│   ├── audit.js           # Audit log writer (response finish hook)
│   └── errorHandler.js    # Global error handler
└── services/
    └── db.js              # PostgreSQL connection pool
```

[VERIFY: clinical-platform/backend/express/src/server.js:1-46]
[VERIFY: clinical-platform/backend/express/src/routes/auth.js:1-85]
[VERIFY: clinical-platform/backend/express/src/routes/proxy.js:1-25]
[VERIFY: clinical-platform/backend/express/src/middleware/auth.js:1-34]
[VERIFY: clinical-platform/backend/express/src/middleware/rbac.js:1-12]
[VERIFY: clinical-platform/backend/express/src/middleware/audit.js:1-30]
[VERIFY: clinical-platform/backend/express/src/middleware/errorHandler.js:1-11]
[VERIFY: clinical-platform/backend/express/src/services/db.js:1-4]

### 4.2 FastAPI Domain Modules

```
backend/fastapi/app/
├── main.py                # FastAPI app, CORS, 8 router includes
├── api/
│   ├── patients.py        # CRUD /api/patients
│   ├── dental.py          # Odontogram chart: /api/patients/{id}/dental-chart
│   ├── orthopedic.py      # Skeleton chart: /api/patients/{id}/skeleton
│   ├── appointments.py    # CRUD /api/patients/{id}/appointments
│   ├── patient_history.py # Medical history, allergies, medications
│   ├── patient_overview.py# Aggregated patient dashboard
│   ├── drugs.py           # Drug resolve, search, interaction check
│   └── chat.py            # AI patient assistant chat
├── services/
│   ├── auth_context.py    # Extract UserContext from proxy headers
│   ├── dental/
│   │   └── numbering.py   # FDI ↔ Universal ↔ Palmer tooth numbering
│   └── drugs/
│       ├── provider.py    # DrugProvider ABC + DrugConcept model
│       ├── rxnorm.py      # RxNorm REST API client
│       └── interactions.py# Drug-drug interaction checker
├── rag/
│   ├── embeddings.py      # sentence-transformers or hash fallback
│   ├── retrieval.py       # HybridRetriever (pgvector + Tavily + RRF)
│   └── tavily.py          # Tavily web search client
├── ai/
│   └── patient_assistant.py # Patient-scoped AI chat (rule-based synthesis)
├── schemas/
│   └── patient.py         # Pydantic models for Patient CRUD
└── models/
    └── database.py        # SQLAlchemy engine + session factory
```

[VERIFY: clinical-platform/backend/fastapi/app/main.py:1-32]
[VERIFY: clinical-platform/backend/fastapi/app/api/ (8 route modules)]
[VERIFY: clinical-platform/backend/fastapi/app/services/ (3 service modules)]
[VERIFY: clinical-platform/backend/fastapi/app/rag/ (3 RAG modules)]
[VERIFY: clinical-platform/backend/fastapi/app/ai/patient_assistant.py:1-156]

### 4.3 Frontend Modules

```
frontend/
├── index.html             # SPA shell
├── css/
│   ├── variables.css      # CSS custom properties
│   ├── layout.css         # Grid layouts
│   ├── components.css     # Component styles
│   ├── dental.css         # Odontogram-specific styles
│   └── skeleton.css       # Skeleton chart styles
└── js/
    ├── app.js             # SPA router (RoleSelection → Auth → Dashboard)
    ├── api.js             # HTTP client with JWT
    ├── pages/
    │   ├── dashboard.js   # Main dashboard cards
    │   ├── skeleton.js    # Orthopedic skeleton page
    │   └── (auth.js, role-selection.js — referenced but not in tree)
    └── components/
        ├── odontogram.js  # Tooth SVG renderer
        └── skeleton-svg.js# Body skeleton SVG renderer
```

[VERIFY: clinical-platform/frontend/js/app.js:1-33 — SPA entry point]
[VERIFY: clinical-platform/frontend/js/api.js:1-16 — API client]
[VERIFY: clinical-platform/frontend/js/components/odontogram.js:1-76]
[VERIFY: clinical-platform/frontend/js/components/skeleton-svg.js:1-69]

---

## 5. Data Model Summary (数据模型概览)

### 5.1 Core Tables (schema.sql)

| Table | Purpose | Key Relationships |
|-------|---------|-------------------|
| `roles` | Permission sets (dentist, orthopedist, admin) | — |
| `clinics` | Multi-tenant organization | 1:N → users, patients |
| `users` | Authenticated practitioners | N:1 → clinics; N:M → patients via patient_access |
| `patients` | Patient records | N:1 → clinics |
| `patient_access` | RBAC patient access | Junction: patients × users |
| `appointments` | Scheduled visits | N:1 → patients, users, clinics |
| `audit_logs` | Request audit trail | N:1 → users |
| `attachments` | File attachments | N:1 → patients |

[VERIFY: clinical-platform/database/schema.sql:1-124 — All 8 core tables + indexes + default roles]

### 5.2 Domain Extension Tables

| Migration | Tables | Domain |
|-----------|--------|--------|
| 002_dental | `dental_charts`, `teeth`, `tooth_events` | Dental odontology |
| 003_orthopedic | `orthopedic_charts`, `body_regions`, `bones`, `bone_events` | Orthopedic skeleton |
| 004_enrichment | `medical_histories`, `allergies`, `medications` | Patient enrichment |
| 005_drugs | `drug_concepts`, `drug_aliases`, `drug_interactions`, `drug_cache` | Drug intelligence |
| 006_rag | `knowledge_documents`, `knowledge_chunks`, `rag_citations`, `rag_queries` | RAG / AI |

[VERIFY: clinical-platform/database/migrations/002_dental.sql:1-44]
[VERIFY: clinical-platform/database/migrations/003_orthopedic.sql:1-55]
[VERIFY: clinical-platform/database/migrations/004_patient_enrichment.sql:1-42]
[VERIFY: clinical-platform/database/migrations/005_drugs.sql:1-44]
[VERIFY: clinical-platform/database/migrations/006_rag.sql:1-47]

---

## 6. Request Flow (请求流)

### 6.1 Authenticated API Request

```
Browser
  │
  ├─ POST /api/auth/login          → Express auth.js → PostgreSQL
  │   └─ Returns: JWT token + refreshToken
  │
  ├─ GET /api/patients             → Express proxy.js
  │   ├─ authenticate() middleware → JWT verify → req.user populated
  │   ├─ createProxyMiddleware()   → Forwards to FastAPI :8000
  │   ├─ onProxyReq:              → Injects x-user-id, x-user-role, x-clinic-id
  │   └─ FastAPI: get_user_context() → Extracts UserContext from headers
  │
  └─ GET /api/patients/{id}/dental-chart
      ├─ Express: authenticate → proxy → headers injection
      └─ FastAPI: dental.py → _ensure_chart() → DB query → ToothOut[]
```

[VERIFY: clinical-platform/backend/express/src/routes/auth.js:38-65 — Login flow]
[VERIFY: clinical-platform/backend/express/src/routes/proxy.js:6-25 — Proxy with header injection]
[VERIFY: clinical-platform/backend/fastapi/app/services/auth_context.py:11-22 — Header extraction]

### 6.2 AI Chat Request

```
Browser → POST /api/chat/patient
  │  Body: { patient_id, message, context? }
  │
  ├─ Express: authenticate → proxy → headers
  │
  └─ FastAPI: chat.py
      ├─ PatientAssistant.chat(db, patient_id, message)
      │   ├─ _gather_patient_context() → 5 DB queries:
      │   │   ├─ patients (identity)
      │   │   ├─ medications (active drugs)
      │   │   ├─ allergies
      │   │   ├─ medical_histories
      │   │   ├─ tooth_events (last 10)
      │   │   └─ bone_events (last 10)
      │   │
      │   ├─ HybridRetriever.retrieve(db, message, patient_id)
      │   │   ├─ _local_search() → embed_text() → pgvector cosine similarity
      │   │   ├─ _tavily_search() → Tavily REST API
      │   │   └─ Reciprocal Rank Fusion (k=60)
      │   │
      │   └─ Synthesize PatientChatResponse (rule-based, no LLM)
      │       ├─ summary (concatenated facts)
      │       ├─ clinical safety disclaimers
      │       └─ citations (from retrieved chunks)
      │
      └─ Return PatientChatResponse
```

[VERIFY: clinical-platform/backend/fastapi/app/api/chat.py:22-31]
[VERIFY: clinical-platform/backend/fastapi/app/ai/patient_assistant.py:43-156]
[VERIFY: clinical-platform/backend/fastapi/app/rag/retrieval.py:19-78]

---

## 7. Security Model (安全模型)

| Layer | Mechanism | Implementation |
|-------|-----------|----------------|
| **Transport** | HTTPS (via helmet) | Express `helmet()` middleware |
| **Authentication** | JWT (HS256) | `auth.js:generateToken()` — 15min expiry |
| **Refresh** | Long-lived JWT | `auth.js:generateRefreshToken()` — 7 day expiry |
| **Authorization** | Role-based (RBAC) | `rbac.js:requireRole()` — dentist/orthopedist/admin |
| **Patient Access** | Clinic scoping | `UserContext.clinic_id` checked in every FastAPI endpoint |
| **Rate Limiting** | 100 req / 15 min | Express `rateLimit()` |
| **Audit** | Full request logging | `audit.js` — logs method, path, status, duration, IP |
| **Password** | bcrypt (cost 12) | `auth.js:22` — `bcrypt.hash(password, 12)` |

[VERIFY: clinical-platform/backend/express/src/middleware/auth.js:4-34]
[VERIFY: clinical-platform/backend/express/src/middleware/rbac.js:1-12]
[VERIFY: clinical-platform/backend/express/src/middleware/audit.js:1-30]
[VERIFY: clinical-platform/backend/express/src/server.js:20-24 — helmet, cors, rateLimit]

---

## 8. Deployment (部署)

```bash
docker compose up --build
```

**Volumes**:
- `postgres_data` — persistent PostgreSQL data
- `database/schema.sql` → mounted as init script

**Health checks**:
- PostgreSQL: `pg_isready -U clinical -d clinical_platform` (5s interval)
- Redis: `redis-cli ping` (5s interval)

[VERIFY: clinical-platform/docker-compose.yml:1-57]

---

## 9. Key Design Decisions (关键设计决策)

### 9.1 Gateway Pattern
Express serves as the single entry point for the browser. It handles auth, serves static files, and proxies all `/api/*` to FastAPI. This allows:
- JWT authentication at the gateway (FastAPI never sees raw tokens)
- Rate limiting at the edge
- Audit logging of all requests
- Static file serving from the same origin

### 9.2 Header-Based Auth Context
FastAPI never validates JWTs. Instead, Express injects `x-user-id`, `x-user-role`, `x-clinic-id` headers after JWT verification. FastAPI trusts these headers because it's only accessible internally.

[VERIFY: clinical-platform/backend/express/src/routes/proxy.js:15-20 — Header injection]
[VERIFY: clinical-platform/backend/fastapi/app/services/auth_context.py:11-22 — Header extraction]

### 9.3 Domain-Specific Visual Charts
Dental and orthopedic domains use interactive SVG-based visualizations:
- **Odontogram**: Tooth-by-tooth SVG with state coloring (healthy, caries, restored, missing, etc.)
- **Skeleton**: Body region SVG with worst-state coloring per region

[VERIFY: clinical-platform/frontend/js/components/odontogram.js:1-76]
[VERIFY: clinical-platform/frontend/js/components/skeleton-svg.js:1-69]

### 9.4 Lazy Chart Initialization
Dental and orthopedic charts are created on-demand when first accessed for a patient. The `_ensure_chart()` / `_ensure_skeleton()` functions create the chart and seed all teeth/bones if none exist.

[VERIFY: clinical-platform/backend/fastapi/app/api/dental.py:71-98 — _ensure_chart()]
[VERIFY: clinical-platform/backend/fastapi/app/api/orthopedic.py:125-162 — _ensure_skeleton()]

### 9.5 Hybrid RAG (Local + Web)
The RAG pipeline combines:
1. **Local**: pgvector cosine similarity search on `knowledge_chunks`
2. **Web**: Tavily API for external clinical evidence
3. **Fusion**: Reciprocal Rank Fusion (k=60) merges both result sets

[VERIFY: clinical-platform/backend/fastapi/app/rag/retrieval.py:52-78 — RRF fusion]

### 9.6 Pluggable Embedding Model
`embeddings.py` tries to load `all-MiniLM-L6-v2` from sentence-transformers. If unavailable (no ML deps), it falls back to a deterministic hash-based pseudo-embedding. The demo runs without GPU or heavy ML packages.

[VERIFY: clinical-platform/backend/fastapi/app/rag/embeddings.py:1-58 — Model loading + fallback]

---

## 10. Technology Matrix (技术矩阵)

| Layer | Technology | Version/Variant |
|-------|-----------|----------------|
| **Runtime (gateway)** | Node.js + Express | ES modules |
| **Runtime (backend)** | Python + FastAPI | uvicorn |
| **Database** | PostgreSQL + pgvector | pg16 with vector extension |
| **Cache** | Redis | 7-alpine (declared, unused) |
| **ORM** | SQLAlchemy (raw text queries) | No model mapping |
| **Validation** | Pydantic v2 | FastAPI native |
| **Auth** | jsonwebtoken (HS256) | 15min access, 7d refresh |
| **Password Hashing** | bcryptjs | Cost factor 12 |
| **HTTP Client** | httpx (async) | For RxNorm + Tavily |
| **Embeddings** | sentence-transformers | all-MiniLM-L6-v2 (384→1536 padded) |
| **Vector Search** | pgvector ivfflat | cosine distance, lists=100 |
| **Web Search** | Tavily API | REST, async |
| **Drug Database** | RxNorm API | REST (rxnav.nlm.nih.gov) |
| **Frontend** | Vanilla JS (ES modules) | No framework |
| **Containerization** | Docker Compose | v3.8 |
