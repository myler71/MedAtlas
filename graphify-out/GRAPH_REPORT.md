# Graph Report - clinical-platform  (2026-08-17)

## Corpus Check
- 61 files · ~13,537 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 328 nodes · 656 edges · 21 communities (16 shown, 5 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 11 edges (avg confidence: 0.61)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6d4efc5e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- drugs.py
- apiCall
- TavilyClient
- dependencies
- dental.py
- UserContext
- RxNormProvider
- orthopedic.py
- patients.py
- server.js
- DrugCheckerPage
- AIAssistantPage
- seed.sh
- README.md
- test-auth-patient.sh

## God Nodes (most connected - your core abstractions)
1. `UserContext` - 43 edges
2. `apiCall()` - 18 edges
3. `RxNormProvider` - 13 edges
4. `get_dental_chart()` - 12 edges
5. `get_skeleton()` - 11 edges
6. `TavilyClient` - 10 edges
7. `get_user_context()` - 10 edges
8. `get_db()` - 9 edges
9. `DrugConcept` - 9 edges
10. `DrugCheckerPage` - 9 edges

## Surprising Connections (you probably didn't know these)
- `createProxyRouter()` --indirect_call--> `authenticate()`  [INFERRED]
  backend/express/src/routes/proxy.js → backend/express/src/middleware/auth.js
- `list_appointments()` --references--> `UserContext`  [EXTRACTED]
  backend/fastapi/app/api/appointments.py → backend/fastapi/app/services/auth_context.py
- `create_appointment()` --references--> `UserContext`  [EXTRACTED]
  backend/fastapi/app/api/appointments.py → backend/fastapi/app/services/auth_context.py
- `update_appointment()` --references--> `UserContext`  [EXTRACTED]
  backend/fastapi/app/api/appointments.py → backend/fastapi/app/services/auth_context.py
- `delete_appointment()` --references--> `UserContext`  [EXTRACTED]
  backend/fastapi/app/api/appointments.py → backend/fastapi/app/services/auth_context.py

## Import Cycles
- None detected.

## Communities (21 total, 5 thin omitted)

### Community 0 - "drugs.py"
Cohesion: 0.07
Nodes (41): AppointmentCreate, AppointmentOut, Config, create_appointment(), delete_appointment(), list_appointments(), BaseModel, delete (+33 more)

### Community 1 - "apiCall"
Cohesion: 0.08
Nodes (12): apiCall(), App, Odontogram, TOOTH_STATE_CLASSES, SkeletonSVG, STATE_CLASSES, AuthPage, Dashboard (+4 more)

### Community 2 - "TavilyClient"
Cohesion: 0.11
Nodes (20): Citation, PatientAssistant, PatientChatResponse, Any, BaseModel, Session, UUID, embed_text() (+12 more)

### Community 3 - "dependencies"
Cohesion: 0.07
Nodes (29): dependencies, bcryptjs, cors, dotenv, express, express-rate-limit, helmet, http-proxy-middleware (+21 more)

### Community 4 - "dental.py"
Cohesion: 0.14
Nodes (28): Config, create_tooth_event(), DentalChartOut, _derive_state(), _ensure_chart(), get_dental_chart(), list_tooth_events(), BaseModel (+20 more)

### Community 5 - "UserContext"
Cohesion: 0.24
Nodes (25): AllergyCreate, AllergyOut, Config, create_allergy(), create_medical_history(), create_medication(), delete_allergy(), delete_medical_history() (+17 more)

### Community 6 - "RxNormProvider"
Cohesion: 0.17
Nodes (12): ABC, DrugInteraction, DrugInteractionService, InteractionCheckResult, BaseModel, Session, DrugConcept, DrugProvider (+4 more)

### Community 7 - "orthopedic.py"
Cohesion: 0.25
Nodes (18): BodyRegionOut, BoneEventCreate, BoneEventOut, BoneOut, Config, create_bone_event(), _derive_bone_state(), _ensure_skeleton() (+10 more)

### Community 8 - "patients.py"
Cohesion: 0.21
Nodes (16): create_patient(), delete_patient(), get_patient(), list_patients(), delete, get, post, put (+8 more)

### Community 9 - "server.js"
Cohesion: 0.20
Nodes (10): auditMiddleware(), pool, authenticate(), generateRefreshToken(), generateToken(), errorHandler(), authRouter, createProxyRouter() (+2 more)

## Knowledge Gaps
- **27 isolated node(s):** `name`, `version`, `type`, `start`, `dev` (+22 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `UserContext` connect `UserContext` to `drugs.py`, `patients.py`, `dental.py`, `orthopedic.py`?**
  _High betweenness centrality (0.214) - this node is a cross-community bridge._
- **Why does `PatientAssistant` connect `TavilyClient` to `drugs.py`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Why does `RxNormProvider` connect `RxNormProvider` to `drugs.py`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `RxNormProvider` (e.g. with `DrugInteraction` and `DrugInteractionService`) actually correct?**
  _`RxNormProvider` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `version`, `type` to the rest of the system?**
  _27 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `drugs.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07183673469387755 - nodes in this community are weakly interconnected._
- **Should `apiCall` be split into smaller, more focused modules?**
  _Cohesion score 0.07568027210884354 - nodes in this community are weakly interconnected._