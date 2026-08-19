# 00 — Current-State Audit

> Verified against the repository (branch `master`, 6 commits) in August 2026. Every section cites file paths. Anything not yet runtime-verified is marked ⚠.

## Architecture (verified)

`backend/express` (gateway, port 3000) → proxies `/api` → `backend/fastapi` (domain backend, port 8000) → PostgreSQL 16 + pgvector. Redis service defined in compose but **unused in code**. Frontend is raw Vanilla JS ES modules served statically by Express (SPA fallback already present in `backend/express/src/server.js`).

| Layer | Tech | Evidence |
|---|---|---|
| Gateway | Express + helmet/cors/json, express-rate-limit (100/15m, in-memory), JWT (access 15m, refresh 7d), bcrypt, audit middleware, http-proxy-middleware | `backend/express/src/server.js`, `backend/express/package.json` |
| Domain API | FastAPI 0.115, SQLAlchemy (mostly raw SQL), pgvector, httpx (Tavily/RxNorm) | `backend/fastapi/requirements.txt`, `backend/fastapi/app/main.py` |
| DB | PostgreSQL 16 + pgvector; schema + numbered SQL migrations (no Alembic) | `database/schema.sql`, `database/migrations/` |
| Frontend | Vanilla JS ES modules, no build step, no framework | `frontend/index.html`, `frontend/js/` (18 files, ~1.1k LOC) |

## API surface (verified exists)

| Domain | Endpoints | File |
|---|---|---|
| Auth | POST `/api/auth/register`, `/api/auth/login`, GET `/api/auth/me`, POST `/api/auth/logout` | `backend/express/src/routes/auth.js` |
| Patients | GET/POST `/api/patients`, GET/PUT/DELETE `/api/patients/{id}` (search via `?search=`, clinic-scoped list) | `backend/fastapi/app/api/patients.py` |
| Dental | GET `/api/patients/{id}/dental-chart`; tooth events GET/POST/PUT | `backend/fastapi/app/api/dental.py` |
| Orthopedic | GET `/api/patients/{id}/skeleton`; bone events GET/POST/PUT | `backend/fastapi/app/api/orthopedic.py` |
| History | medical histories / allergies / medications CRUD | `backend/fastapi/app/api/patient_history.py` |
| Appointments | CRUD under `/api/patients/{id}/appointments` | `backend/fastapi/app/api/appointments.py` |
| Drugs | POST `/drugs/resolve`, GET `/drugs/search`, POST `/drug-interactions/check` | `backend/fastapi/app/api/drugs.py`, `interactions.py` |
| Assistant | POST `/api/chat/patient` (citations + missing_information in response) | `backend/fastapi/app/api/chat.py` |

## Frontend inventory (verified)

| File | State |
|---|---|
| `js/app.js` | Linear state flow (RoleSelection → Auth → Dashboard). **No router.** |
| `js/api.js` | fetch + Bearer from localStorage; throws on non-OK; **no 401 handling**; base hardcoded `http://localhost:3000` |
| `js/pages/role-selection.js`, `auth.js` | Client-side role selector; login/register. To be merged into one login page. |
| `js/pages/dashboard.js` | Cards are **non-functional**; logout works; unused `apiCall` import |
| `js/pages/patient-overview.js` | Overview + role-gated chart buttons; loading/error states; **never instantiated** |
| `js/pages/dental-chart.js` | Tooth details + event history + Add Event. Working flow. |
| `js/pages/skeleton.js` | Region/bone detail + events + event form. Working flow. |
| `js/pages/drug-checker.js` | Class exists, **never instantiated**; already contains the "no interaction found ≠ safe" wording |
| `js/pages/ai-assistant.js` | Class exists, **never instantiated**; already renders citations + missing_information |
| `js/components/odontogram.js` | 9 states, FDI quadrants, all teeth share one hardcoded path; click-only — **no keyboard/ARIA** |
| `js/components/skeleton-svg.js` | 8 states, backend-driven `svg_path` regions, worst-state priority; no orientation logic, no keyboard/ARIA |
| `css/variables.css`, `layout.css`, `components.css` | Tokenized blue/slate palette, system font, grid/card utilities. Linked in `index.html`. |
| `css/dental.css`, `skeleton.css` | State colors + fixed detail panel/timeline. **NOT linked in `index.html`** → charts render unstyled. |

## API-to-screen map (verified)

Every frontend-referenced endpoint exists in FastAPI. Frontend references: dental chart GET (`odontogram.js:26`), skeleton GET (`skeleton-svg.js:25`), login/register (`auth.js:44`), tooth events GET/POST (`dental-chart.js:43,90`), bone events GET/POST (`skeleton.js:42,101`), chat (`ai-assistant.js:114`), interaction check (`drug-checker.js:73`), overview/allergies/meds/medical-history (`patient-overview.js:48,55-57`). **No frontend references to appointments or patient-list/search endpoints** → those are net-new UI against existing APIs.

## Reusable assets

- Both SVG chart components — clean class APIs, stable constructors (`container, patientId, onSelect*`)
- `drug-checker.js` honest no-result wording; `ai-assistant.js` citations/missing-info layout
- CSS variables + layout/composite grid already tokenized
- Backend supports **all 8 MVP capabilities** with real persistence

## Broken / missing / risky (verified)

| Severity | Finding | Evidence |
|---|---|---|
| 🔴 Demo blocker | `docker compose up` initializes **only** `schema.sql`; migrations 002–006, `seed.sql`, and `seeds/drug_interactions.sql` are never applied → domain tables/data missing | `docker-compose.yml` postgres init |
| 🔴 Demo blocker | `seed.sql` password hashes are literal placeholders → seeded users cannot log in | `database/seed.sql:7-10` |
| 🔴 Dead end | After login, dashboard cards are static → no way to reach any clinical page | `dashboard.js`, no instantiations |
| 🔴 Broken styling | `dental.css` + `skeleton.css` not linked | `index.html:6-9` |
| 🟠 Unverified security | FastAPI trusts `x-user-id/x-user-role/x-clinic-id` headers only — safe only if FastAPI is not directly reachable | `backend/fastapi/app/auth_context.py` |
| 🟠 Contract gaps | `requireRole` middleware wired to zero routes; `patient_access` table has no enforcement; refresh-token flow incomplete; clinic scope missing on several update/delete endpoints | `backend/express/src/middleware/rbac.js`, `database/schema.sql`, route files |
| 🟠 Observability | Audit middleware mounted before auth → `req.user` often unset | `server.js` (middleware order) |
| 🟠 Reliability | Odontogram/skeleton loads have no loading state and no `.catch`; API client has no 401 handling, no error normalization | `odontogram.js`, `skeleton-svg.js`, `api.js` |
| 🟡 Tests | Only `tests/test-auth-patient.sh` (bash/curl). No unit/E2E framework. | `tests/` |
| 🟡 Tooling | No lint/build commands; README quick start ("open index.html") fails for ES modules over `file://` | `README.md` |
| 🟡 VCS hygiene | `graphify-out/` (thousands of generated files) untracked — add to `.gitignore` | repo root |

## Architectural constraints (preserve)

- **Express → FastAPI trust boundary**: do not change without an approved, documented reason
- **No public API contract changes** without documenting reason, clients, migration path, approval
- Clinic-scoped data model; synthetic demo data (and password hashes) must remain demo-only, clearly labeled
- The assistant is **rule-based decision support** (no external LLM) — keep honest about this in UI copy
- Drug interaction results are **preseeded-DB-lookup only** — never display "no interaction found" as evidence of safety