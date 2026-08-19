# 05 — Implementation Plan

**Approach:** Approach A — build-less componentized Vanilla JS + hash router (see `04-frontend-architecture.md` for the ADR). **Timeline: ≈4–6 working days**, compressible by descoping M6 stretch items.

**Mandatory-backend-change rule:** exactly 3 items — (1) real bcrypt hashes in `seed.sql`, (2) compose initdb mounts for migrations 002–006 + `seed.sql` + `seeds/drug_interactions.sql`, (3) README quick-start. **Zero API contract changes.** Everything else backend is P1/P2 (documented in `08-decision-log.md`).

## Milestones

| M | Name | Est. | Definition of done (pick) |
|---|---|---|---|
| M1 | Foundation | 0.5–1d | Cold `docker compose down -v && up --build` → curl-verified login at `:3000` → shell + dashboard; 401 redirect works; dental.css returns 200 |
| M2 | Patient discovery & context | 0.5–1d | Search "john"→John Smith; deep link to `#/patients/:id` in fresh tab; role-gated nav; back/forward correct |
| M3 | Dental vertical | ~1d | Tab reaches all 32 teeth; Enter opens drawer; Esc closes + restores focus; event-add updates state in place; all 9 states in legend with text |
| M4 | Orthopedic vertical | ~0.5d | Same as M3; worst-state visible in labels/legend/list |
| M5 | Medications + assistant | ~1d | warfarin+aspirin → major interaction with source/evidence; zero-result shows explicit caveat; answer shows citations + missing-info; keyboard-operable |
| M6 | Demo polish & verification | ~1d | Golden path runs from cold stack; every P0 checklist row evidenced (`verification.md`); a11y + responsive pass |

## Tasks (required format)

Each task below uses the mandated format. All P0 tasks are sized for a subagent to execute without silent product/architecture decisions.

### M1 — Foundation

**T-1.1 — Seed real credentials (P0)**
- **Objective:** seeded users can log in from a fresh stack. **User value:** the single most common demo failure.
- **Owner/Reviewer:** executor / code-reviewer.
- **Files:** `database/seed.sql`.
- **Dependencies:** none. Decisions: none (documented in decision log).
- **Details:** replace placeholder hashes (`seed.sql:7-10`) with real bcrypt (12 rounds) for `dentist@clinic.com`, `orthopedist@clinic.com`, `admin@clinic.com` (verify emails/roles from seed). Hash command: `docker compose exec express node -e "console.log(require('bcryptjs').hashSync('password123', 12))"`.
- **Acceptance:** documented credentials log in via `POST /api/auth/login`.
- **Validation:** `curl.exe -s -X POST http://localhost:3000/api/auth/login -H "Content-Type: application/json" -d '{"email":"dentist@clinic.com","password":"password123"}'` returns a token.
- **Evidence:** curl output; no placeholder hash remains in seed.sql.
- **Rollback:** single-line revert.

**T-1.2 — One-command seeded stack (P0)**
- **Objective:** `docker compose up --build` produces a fully seeded, loginable DB.
- **Owner/Reviewer:** executor / code-reviewer.
- **Files:** `docker-compose.yml`.
- **Dependencies:** none. Decisions: named initdb mounts (keep existing schema.sql as first; apply `database/migrations/00*.sql` in numeric order, then `seed.sql`, then `seeds/drug_interactions.sql`).
- **Details:** configure postgres init with all SQL files; confirm idempotency (migrations use `CREATE TABLE IF NOT EXISTS` — verify; else note ordering).
- **Acceptance:** fresh volume → all domain tables + 2 patients + 10 drug concepts + 8 interaction pairs present; health endpoints green.
- **Validation:** `docker compose down -v; docker compose up --build -d; curl.exe -s http://localhost:3000/api/health; docker compose exec postgres psql -U <user> -d <db> -c "select count(*) from patients;"`.
- **Evidence:** command output.
- **Rollback:** revert compose file.

**T-1.3 — README quick start (P0)**
- **Objective:** documented cold-start works. **Files:** `README.md`.
- **Details:** entry URL `http://localhost:3000` (not `frontend/index.html`); demo credentials; reset command `docker compose down -v`; link to `docs/ui-redesign/10-demo-script.md`.
- **Acceptance:** a stranger can start + log in from the README alone.

**T-1.4 — Router, auth, shell (P0)**
- **Files:** `js/router.js` (NEW), `js/auth.js` (NEW), `js/shell.js` (NEW), `js/app.js` (REW), `js/api.js` (REW), `js/pages/login.js` (NEW; delete `role-selection.js` + `auth.js`), `index.html`, `css/variables|layout|components.css`.
- **Details:** routes per `02-information-architecture.md`; API hardening per `04-frontend-architecture.md` (401 → `#/login?expired=1` + toast; `location.origin`; `ApiError`); link `dental.css` + `skeleton.css`; skip-link + `#shell`/`#view` mounts; merge role selector into login (label demo-only).
- **Acceptance:** login → dashboard; nav filtered by role; 401 redirects; dental.css serves 200.

### M2 — Patient discovery & context

**T-2.1 — Patient list/search (P0)** — `js/pages/patients.js`
Debounced (250ms) search → `GET /api/patients?search=`; table (Name/DOB/Phone/Created); row→`#/patients/:id`; skeleton/empty/error states; keyboard rows.

**T-2.2 — Patient overview (P0)** — `js/pages/patient-overview.js` (REW)
Route-driven; summary cards; meds/allergies/medical history; recent events table; entry buttons to dental/skeleton/assistant (role-gated); loading/error states.

**T-2.3 — Live dashboard (P0)** — `js/pages/dashboard.js` (REW)
Today's queue/appointments + recent patients + role-aware shortcuts; no dead cards.

### M3 — Dental vertical

**T-3.1 — Odontogram a11y + legend (P0)** — `js/components/odontogram.js`, `js/components/state-legend.js` (NEW), `css/dental.css`, `css/charts.css` (NEW)
Native-button teeth; aria-labels `Tooth N (FDI), region, state: X`; legend shape+text for all 9 states; text list alternative; constructor API unchanged.
**T-3.2 — Tooth detail drawer (P0)** — `js/components/drawer.js` (NEW), `js/pages/dental-chart.js` (MOD)
Drawer: state + history + Add Event (POST; pending-disable; success toast; in-place refresh; error banner).

### M4 — Orthopedic vertical

**T-4.1 — Skeleton a11y + legend (P0)** — `js/components/skeleton-svg.js`, `js/components/state-legend.js`, `css/skeleton.css`, `css/charts.css`
Region paths `role=button tabindex=0` + Enter/Space; labels incl. worst-state; region→bone list alternative; orientation in labels.
**T-4.2 — Region/bone drawer (P0)** — `js/components/drawer.js`, `js/pages/skeleton.js` (MOD)
Mirror of M3; event flow preserved.

### M5 — Medications + assistant

**T-5.1 — Drug checker wired (P0)** — `js/pages/drug-checker.js` (MOD)
Route `#/drug-checker`; labelled chips; severity badges icon+text+color; prefill from `?patient=:id`; **keep existing "no interaction found ≠ safe" wording verbatim**; unused-drug states honest.
**T-5.2 — Assistant wired (P0)** — `js/pages/ai-assistant.js` (MOD)
Route `#/patients/:id/assistant`; persistent decision-support banner ("Decision support only — not a substitute for clinical judgment"); citations + missing-info + safety sections; loading/error states.

### M6 — Demo polish & verification

**T-6.1 — A11y sweep (P0)** — labels, contrast tokens, focus order, list-alternative default <760px, tables→cards.
**T-6.2 — Responsive pass (P1)** — 1280/820/390 documented; charts use Chart/List toggle at small widths.
**T-6.3 — Demo script + verification.md (P0)** — README demo script (5–10 min); `docs/ui-redesign/verification.md` checklist mapped to quality gates.
**T-6.4 — Golden-path E2E (stretch/P1)** — `tests/e2e/golden-path.spec.js` (Playwright: login → search → overview → dental event → skeleton event → drug check → assistant; axe serious/critical = 0/page).
**T-6.5 — Appointments UI (stretch/P1)** — `js/pages/appointments.js` (backend CRUD exists).

## Dependencies & approval gates

G0 (plan approval) → G1 (spec review of the `docs/ui-redesign/` set) → **M1 → G2 (M1 evidence revieew) → M2 → G3 → M3 → G4 → M4 → G5 → M5 → G6 → M6 → G7 (quality gates: full evidence review) → final approval gate.**

Each M gate requires: tests/verification commands run, evidence recorded in `verification.md`, code-reviewer approval.

## Risks & relative effort

Top risks: (1) seeding reproducibility — mitigated declaratively in T-1.1/1.2 and curl-gated; (2) mid-demo JWT expiry — graceful 401 floor (T-1.4) + P1 env-tunable TTL; (3) in-memory rate limit during click-heavy demo — P1 env-tunable; (4) Vanilla scope creep — frozen component inventory (03-design-system) + router <150 LOC; (5) a11y retro-fit cost — native-button wrapping only (no custom widgets).

Effort notation: P0 core M1–M5 ≈ 3.5–4.5d; M6 ≈ 1d incl. stretch. Commands are deliberately PowerShell-safe (`curl.exe`).