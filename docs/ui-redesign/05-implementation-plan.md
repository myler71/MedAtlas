# 05 — Implementation Plan

**Approach:** Approach A — build-less componentized Vanilla JS + hash router (see `04-frontend-architecture.md` for the ADR). **Timeline: ≈4–6 working days**, compressible by descoping M6 stretch items.

**Mandatory-backend-change rule:** exactly 3 grouped workstreams — (1) real bcrypt hashes in `seed.sql`, (2) compose initdb mounts for migrations 002–006 + `seed.sql` + `seeds/drug_interactions.sql`, (3) demo-data seed (`database/seeds/demo_clinical.sql`, new — allergies/meds/history/chart events/patient↔drug for the two seeded patients) **+ README quick-start (same workstream, docs)**. **Zero API contract changes.** Everything else backend is P1/P2 (documented in `08-decision-log.md`).

## Milestones

| M | Name | Est. | Definition of done (pick) |
|---|---|---|---|
| M1 | Foundation | 0.5–1d | Cold `docker compose down -v && up --build` → curl-verified login at `:3000` → shell + dashboard; 401 redirect works; dental.css returns 200 |
| M2 | Patient discovery & context | 0.5–1d | Search "john"→John Smith; deep link to `#/patients/:id` in fresh tab; role-gated nav; back/forward correct |
| M3 | Dental vertical | ~1d | Tab reaches all 32 teeth; Enter opens drawer; Esc closes + restores focus; event-add updates state in place; all 9 states in legend with text |
| M4 | Orthopedic vertical | ~0.5d | Same as M3; worst-state visible in labels/legend/list |
| M5 | Medications + assistant | ~1d | warfarin+aspirin → major interaction with source/evidence; zero-result shows explicit caveat; answer shows citations + missing-info; keyboard-operable |
| M6 | Demo polish & verification | ~1d | Golden path runs from cold stack; every P0 checklist row evidenced (`verification.md`); a11y pass (P0); responsive documented at 1280+820 (P0), 390px + chart/list toggle is P1 |

## Tasks (required format)

Each task below uses the mandated format. All P0 tasks are sized for a subagent to execute without silent product/architecture decisions.

### M1 — Foundation

**T-1.1 — Seed real credentials (P0)**
- **Objective:** seeded users can log in from a fresh stack. **User value:** the single most common demo failure.
- **Owner/Reviewer:** executor / code-reviewer.
- **Files:** `database/seed.sql`.
- **Dependencies:** none. Decisions: none (documented in decision log).
- **Details:** replace the two placeholder hashes (`seed.sql:7-10`) with real bcrypt (12 rounds). The **only seeded users are `dentist@clinic.com` (Dr. Sarah Chen) and `ortho@clinic.com` (Dr. James Wilson)** — there is **no seeded admin** (schema has the role; seeding one is P1, `08-decision-log`). NOTE: `database/seed.sh` already exists to regenerate hashes but is never invoked by compose — prefer running it (or `docker compose exec express node -e "console.log(require('bcryptjs').hashSync('password123', 12))"`); keep `seed.sh` out of compose for determinism.
- **Acceptance:** documented credentials log in via `POST /api/auth/login`.
- **Validation:** `curl.exe -s -X POST http://localhost:3000/api/auth/login -H "Content-Type: application/json" -d '{"email":"dentist@clinic.com","password":"password123"}'` returns a token.
- **Evidence:** curl output; no placeholder hash remains in seed.sql.
- **Rollback:** single-line revert.

**T-1.2 — One-command seeded stack (P0)**
- **Objective:** `docker compose up --build` produces a fully seeded, loginable DB.
- **Owner/Reviewer:** executor / code-reviewer.
- **Files:** `docker-compose.yml`.
- **Dependencies:** none. Decisions: named initdb mounts (keep existing `schema.sql` as first; then `database/migrations/002_dental.sql`, `003_orthopedic.sql`, `004_patient_enrichment.sql`, `005_drugs.sql`, `006_rag.sql` in numeric order — **initdb runs files in C-locale filename order, so prefix files if needed or mount each with explicit `<host>:<container>` names**; then `seed.sql`, then `seeds/drug_interactions.sql`, then `seeds/demo_clinical.sql` from T-1.5).
- **Details:** configure postgres init with all SQL files. **Idempotency:** migrations use plain `CREATE TABLE` (verified — no `IF NOT EXISTS`), so initdb is **fresh-volume-only** (`docker compose down -v` between runs); do NOT claim re-runnable initdb. Ordering: schema → migrations 002–006 → seed.sql → drug_interactions.sql → demo_clinical.sql, and each currently empty tables (medical_histories, allergies, medications, dental_charts, tooth_events, etc.) gets its demo rows from the last file.
- **Acceptance:** `docker compose down -v; docker compose up --build -d` → all domain tables + seeded rows present (verify via psql counts); health endpoints green.
- **Validation:** `docker compose down -v; docker compose up --build -d; curl.exe -s http://localhost:3000/api/health; docker compose exec postgres psql -U clinical -d clinical_platform -c "select count(*) from patients;"` (compose env: `POSTGRES_USER=clinical`, `POSTGRES_DB=clinical_platform`).
- **Evidence:** command output; count lines for patients=2, dental_charts=2, allergies>0, medications>0, tooth_events>0.
- **Rollback:** revert compose file; recovery from a partial init = `docker compose down -v && up` (init scripts are idempotent only by virtue of the fresh volume).

**T-1.3 — README quick start (P0)**
- **Objective:** a stranger can start + log in from the README alone. **User value:** demo reproducibility.
- **Owner/Reviewer:** executor / code-reviewer.
- **Files:** `README.md`.
- **Dependencies:** T-1.1 (credentials exist). Decisions: none (documented).
- **Details:** entry URL `http://localhost:3000` (not `frontend/index.html`); demo credentials (`dentist@clinic.com` / `ortho@clinic.com`, `password123`); reset command `docker compose down -v`; link to `docs/ui-redesign/10-demo-script.md` and `docs/ui-redesign/verification.md`.
- **Acceptance:** a stranger can start + log in from the README alone.
- **Validation:** fresh checkout → follow README → login succeeds.
- **Evidence:** README diff; screenshot of successful login.
- **Rollback:** revert README.

**T-1.4 — Router, auth, shell (P0)**
- **Objective:** hash routing + auth session + app shell make every page reachable and role-gated. **User value:** tree-to-dead-end fixed.
- **Owner/Reviewer:** executor / code-reviewer.
- **Files:** `js/router.js` (NEW), `js/auth.js` (NEW), `js/shell.js` (NEW), `js/app.js` (REW), `js/api.js` (REW), `js/pages/login.js` (NEW; delete `role-selection.js` + `auth.js`), `index.html`, `css/variables|layout|components.css`.
- **Dependencies:** none. Decisions: routes per `02-information-architecture.md`; role guards are **client-side UX only** (server enforcement P2).
- **Details:** API hardening per `04-frontend-architecture.md` (401 → `#/login?expired=1` + toast; `location.origin`; `ApiError`); link `dental.css` + `skeleton.css`; skip-link + `<main id="view">` mount; merge role selector into login (label demo-only); `api.js` thin fetch surface.
- **Acceptance:** login → dashboard; nav filtered by role; 401 redirects; dental.css serves 200; deep link `#/patients/:id` in a fresh tab loads.
- **Validation:** `curl.exe -s -o /dev/null -w "%{http_code}" http://localhost:3000/css/dental.css` → 200; browser: login, nav, expired-token redirect, direct hash link.
- **Evidence:** curl output; screenshots; console has no errors.
- **Rollback:** git revert of the M1 commit; the old linear flow remains on `master`.

**T-1.5 — Demo-data seed (P0, prerequisite for capabilities 3–8)**
- **Objective:** the demo's data-bearing steps can run from a cold stack. **User value:** the golden path is honest (previously unsupportable).
- **Owner/Reviewer:** executor / code-reviewer.
- **Files:** `database/seeds/demo_clinical.sql` (NEW) + compose initdb mount (T-1.2).
- **Dependencies:** T-1.2 (mount order). Decisions: demo data is synthetic, clearly labeled, only for patients John Smith + Maria Garcia; values taken from `00-current-state-audit.md` §Seeded synthetic data.
- **Details:** INSERT demo rows referencing the known patient/user UUIDs: allergies (`penicillin`, severe) + medications (`warfarin 5mg`, `aspirin 81mg`, active) + one medical history entry for John Smith; a couple of seeded dental_chart/tooth_events and orthopedic events (dental chart + teeth auto-created by API on first GET — seed events via the API in a one-time setup step **or** seed `dental_charts`/teeth rows directly to match `002_dental.sql`; document whichever is chosen); patient↔drug assignments for the demo pair. All content mirrors `10-demo-script.md` exactly so the demo and the seed never drift.
- **Acceptance:** cold stack → John Smith banner shows penicillin + warfarin/aspirin; dental/ortho charts show seeded events; drug checker resolves warfarin+aspirin to major.
- **Validation:** `docker compose down -v && docker compose up --build -d` then query each demo endpoint via curl (dental chart, skeleton, medications, allergies); count rows.
- **Evidence:** curl/JQ output; row counts; demo script (10) runs its data steps.
- **Rollback:** delete the seed file + its mount; revert.

### M2 — Patient discovery & context

**T-2.1 — Patient list/search (P0)**
- **Objective:** search patients and open one. **User value:** "find a patient in under 30 s".
- **Owner/Reviewer:** executor / code-reviewer.
- **Files:** `js/pages/patients.js` (NEW), `css/components.css` (table/card states).
- **Dependencies:** T-1.4. Decisions: server-side `?search=` (no client filter).
- **Details:** debounced (250ms) search → `GET /api/patients?search=`; table (Name/DOB/Phone/Created); row→`#/patients/:id`; skeleton/empty/error states; keyboard rows.
- **Acceptance:** "smith" returns John Smith; Enter opens the patient.
- **Validation:** browser type "smith"; assert row; keyboard Enter.
- **Evidence:** screenshot; console clean.
- **Rollback:** revert M2 commit.

**T-2.2 — Patient overview (P0)**
- **Objective:** a stable patient landing page with context. **User value:** context in one place.
- **Owner/Reviewer:** executor / code-reviewer.
- **Files:** `js/pages/patient-overview.js` (REW), `js/components/states.js` (NEW), `css/components.css`.
- **Dependencies:** T-1.4, T-1.5 (data exists). Decisions: route-driven; role-gated entry buttons (client UX only).
- **Details:** route-driven; summary cards; meds/allergies/medical history via verified `GET /api/patients/{id}/medications|allergies|medical-history`; recent events table; entry buttons to dental/skeleton/assistant (role-gated); loading/error states.
- **Acceptance:** opening John Smith shows his seeded context; chart buttons reflect role.
- **Validation:** browser open John Smith; assert pills + banner.
- **Evidence:** screenshot; console clean.
- **Rollback:** revert M2 commit.

**T-2.3 — Live dashboard (P0)**
- **Objective:** dashboard is real, not static cards. **User value:** demo opens on live data.
- **Owner/Reviewer:** executor / code-reviewer.
- **Files:** `js/pages/dashboard.js` (REW), `css/layout.css`, `css/components.css`.
- **Dependencies:** T-1.4, T-1.5. Decisions: recent patients from `GET /api/patients` (capped); no aggregate-schedule panel (P1).
- **Details:** recent patients (from `GET /api/patients`, capped) + role-aware shortcuts + actionable alerts where data supports them; **no dead cards**. ⚠ No global appointments schedule API exists (appointments are patient-scoped) — a "today's queue" panel is **deferred to P1** rather than faked.
- **Acceptance:** dashboard shows seeded patients + working shortcuts; no dead cards.
- **Validation:** browser dashboard; click shortcut → route.
- **Evidence:** screenshot.
- **Rollback:** revert M2 commit.

### M3 — Dental vertical

**T-3.1 — Odontogram a11y + legend (P0)**
- **Objective:** every tooth is keyboard- and SR-reachable with a non-color legend. **User value:** a11y gate.
- **Owner/Reviewer:** a11y-focused `code-reviewer` / `qa-tester`.
- **Files:** `js/components/odontogram.js` (MOD), `js/components/state-legend.js` (NEW), `css/dental.css`, `css/charts.css` (NEW).
- **Dependencies:** T-1.4, T-1.5. Decisions: constructor API unchanged; native-button wrapping only.
- **Details:** native-button teeth; aria-labels `Tooth N (FDI), region, state: X`; legend shape+text for all 9 states; text list alternative; constructor API unchanged.
- **Acceptance:** Tab reaches all 32 teeth; legend is shape+text.
- **Validation:** keyboard walkthrough; SR spot-check.
- **Evidence:** keyboard path log; axe/reader notes.
- **Rollback:** revert M3 commit.

**T-3.2 — Tooth detail drawer (P0)**
- **Objective:** view history and record events without losing context. **User value:** documentation UX.
- **Owner/Reviewer:** executor / code-reviewer.
- **Files:** `js/components/drawer.js` (NEW), `js/pages/dental-chart.js` (MOD).
- **Dependencies:** T-3.1. Decisions: drawer pattern (03) — role=dialog, focus trap, Esc, focus restore.
- **Details:** drawer: state + history + Add Event (POST `/api/patients/{id}/dental-chart/teeth/{tid}/events`; pending-disable; success toast; in-place refresh; error banner).
- **Acceptance:** opens tooth history; event POSTs and updates state in place.
- **Validation:** select tooth → Add Event → assert chart + drawer refresh.
- **Evidence:** screenshots; POST captured.
- **Rollback:** revert M3 commit.

### M4 — Orthopedic vertical

**T-4.1 — Skeleton a11y + legend (P0)**
- **Objective:** regions/bones keyboard- and SR-reachable, worst-state visible. **User value:** a11y gate parity with dental.
- **Owner/Reviewer:** a11y-focused `code-reviewer` / `qa-tester`.
- **Files:** `js/components/skeleton-svg.js` (MOD), `js/components/state-legend.js`, `css/skeleton.css`, `css/charts.css`.
- **Dependencies:** T-1.4, T-1.5. Decisions: `role=button tabindex=0` + Enter/Space; worst-state priority retained.
- **Details:** region paths `role=button tabindex=0` + Enter/Space; labels incl. worst-state; region→bone list alternative; orientation in labels.
- **Acceptance:** Tab reaches regions; worst-state in labels/legend/list.
- **Validation:** keyboard walkthrough; SR spot-check.
- **Evidence:** keyboard path log; axe/reader notes.
- **Rollback:** revert M4 commit.

**T-4.2 — Region/bone drawer (P0)**
- **Objective:** orthopedic event documentation in the same drawer pattern. **User value:** consistent workflow.
- **Owner/Reviewer:** executor / code-reviewer.
- **Files:** `js/components/drawer.js`, `js/pages/skeleton.js` (MOD).
- **Dependencies:** T-4.1. Decisions: mirror of M3.
- **Details:** mirror of M3 (GET/POST events under `/api/patients/{id}/skeleton`).
- **Acceptance:** same guarantees as M3 for skeleton.
- **Validation:** select region → Add Event → assert refresh.
- **Evidence:** screenshots.
- **Rollback:** revert M4 commit.

### M5 — Medications + assistant

**T-5.1 — Drug checker wired (P0)**
- **Objective:** interaction checking is reachable and honest. **User value:** safety wording preserved.
- **Owner/Reviewer:** executor / clinical-safety reviewer.
- **Files:** `js/pages/drug-checker.js` (MOD), `css/components.css` (chips/badges).
- **Dependencies:** T-1.4, T-1.5. Decisions: **keep existing "no interaction found ≠ safe" wording verbatim**; severity badges icon+text+color.
- **Details:** route `#/drug-checker`; labelled chips; severity badges icon+text+color; prefill from `?patient=:id`; unused-drug states honest.
- **Acceptance:** warfarin+aspirin → major with source/evidence; no-record pair → explicit caveat (never "safe").
- **Validation:** curl `POST /api/drug-interactions/check` + browser check.
- **Evidence:** curl output; screenshot.
- **Rollback:** revert M5 commit.

**T-5.2 — Assistant wired (P0)**
- **Objective:** patient-scoped Q&A with evidence + safety framing. **User value:** honest decision support.
- **Owner/Reviewer:** executor / clinical-safety reviewer.
- **Files:** `js/pages/ai-assistant.js` (MOD).
- **Dependencies:** T-1.4, T-1.5. Decisions: persistent decision-support banner; rule-based imposter honesty.
- **Details:** route `#/patients/:id/assistant`; persistent decision-support banner ("Decision support only — not a substitute for clinical judgment"); citations + missing-info + safety sections; loading/error states.
- **Acceptance:** answer shows citations + missing-info + banner; degraded state when Tavily down.
- **Validation:** browser ask a seeded-data question; assert sections.
- **Evidence:** screenshots; console clean.
- **Rollback:** revert M5 commit.

### M6 — Demo polish & verification

**T-6.1 — A11y sweep (P0)**
- **Objective:** every P0 screen passes keyboard + contrast. **User value:** accessibility gate evidence.
- **Owner/Reviewer:** a11y-focused `code-reviewer` / `verifier`.
- **Files:** all page/component CSS + components; focus/contrast token updates.
- **Dependencies:** all prior P0. Decisions: non-color states mandatory; list alternative default <760px.
- **Details:** labels, contrast tokens, focus order, list-alternative default <760px, tables→cards.
- **Acceptance:** P0 journeys pass keyboard + AA contrast; axe (where runnable) serious/critical = 0.
- **Validation:** keyboard walkthrough both charts; contrast audit; axe run.
- **Evidence:** `verification.md` a11y rows.
- **Rollback:** revert M6 commit.

**T-6.2 — Responsive pass (P1)**
  *(P1 — abbreviated by explicit exemption; full template not required.)*
- **Details:** 1280/820 documented (P0 floor); 390px + chart/list toggle is P1 — non-goal sub-390px.

**T-6.3 — Demo script + verification.md (P0)**
- **Objective:** anyone can run + verify the demo. **User value:** reviewer reproducibility.
- **Owner/Reviewer:** demo lead / verifier.
- **Files:** `docs/ui-redesign/10-demo-script.md` (MOD), `docs/ui-redesign/verification.md` (populate).
- **Dependencies:** all P0. Decisions: script uses only seeded personas/data (per 00).
- **Details:** README demo script (5–10 min); `verification.md` checklist mapped to quality gates (G0–G7).
- **Acceptance:** golden path runs from cold stack per 10; every P0 row evidenced.
- **Validation:** fresh `docker compose down -v && up --build`; script walkthrough.
- **Evidence:** recorded run; screenshots; `verification.md` filled.
- **Rollback:** revert M6 commit.

**T-6.4 — Golden-path E2E (stretch/P1)**
  *(P1/stretch — abbreviated by explicit exemption.)*
- **Details:** `tests/e2e/golden-path.spec.js` (Playwright: login → search → overview → dental event → skeleton event → drug check → assistant; axe serious/critical = 0/page).

**T-6.5 — Appointments UI (stretch/P1)**
  *(P1/stretch — abbreviated by explicit exemption.)*
- **Details:** `js/pages/appointments.js` (backend CRUD exists under `/api/patients/{id}/appointments`).

## Dependencies & approval gates

G0 (plan approval) → G1 (spec review of the `docs/ui-redesign/` set) → **M1 → G2 (M1 evidence review) → M2 → G3 → M3 → G4 → M4 → G5 → M5 → G6 → M6 → G7 (quality gates: full evidence review) → final approval gate.**

Each M gate requires: tests/verification commands run, evidence recorded in `verification.md`, code-reviewer approval.

## Risks & relative effort

Top risks: (1) seeding reproducibility — mitigated declaratively in T-1.1/1.2/1.5 and curl-gated; (2) mid-demo JWT expiry — graceful 401 floor (T-1.4) + P1 env-tunable TTL; (3) in-memory rate limit during click-heavy demo — P1 env-tunable; (4) Vanilla scope creep — frozen component inventory (03-design-system) + router <150 LOC; (5) a11y retro-fit cost — native-button wrapping only (no custom widgets); (6) demo-data drift between seed and script — T-1.5 mandates seed mirrors `10-demo-script.md`.

Effort notation: P0 core M1–M5 ≈ 3.5–4.5d; M6 ≈ 1d incl. stretch. Commands are deliberately PowerShell-safe (`curl.exe`).