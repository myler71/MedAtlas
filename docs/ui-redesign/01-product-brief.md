# 01 — Product Brief

## Product vision

A **Clinical Care Workspace**: a calm, trustworthy, information-dense application in which a dentist or orthopedist can log in, find a patient, understand the patient's important context in under 30 seconds, document a dental or orthopedic finding, inspect medications and allergies, check interactions, and ask the patient-scoped assistant a question without losing context.

Deliver a polished, accessible, demo-ready workspace that moves from patient discovery to anatomical charting, medication safety review, and evidence-backed patient assistance in one coherent, safe, role-aware workflow.

## Personas & jobs to be done

| Persona | Primary jobs | Demo-critical moments |
|---|---|---|
| **Dentist — Dr. Sarah Chen** (seeded: `dentist@clinic.com`) | Find patient → review allergies/meds → read/sign a tooth chart → record an event | Tooth selection, state legend, event capture, keyboard use |
| **Orthopedist — Dr. James Wilson** (seeded: `ortho@clinic.com`) | Find patient → review context → read region/bone findings → record an event | Region/bone selection, worst-state visibility |
| **Admin** (role exists in schema; **no seeded account** — P1) | Broad visibility across both disciplines; role-gated navigation | Role-gating is demo-accurate, **not** shown as a real login until an admin is seeded |

Model only what the codebase supports. Do not invent front-desk, billing, or insurance personas.

## MVP scope

- **P0 — Essential (golden path):** seeded loginable stack; **demo-data seed** (allergies/meds/history/chart events/patient↔drug assignments for the two seeded patients — required for every data-bearing demo step); hash router + app shell; patient list/search → patient overview → dental chart → skeleton chart → medication checker → assistant; persistent patient header; loading/empty/error/permission states; keyboard + non-color accessibility; honest decision-support framing.
- **P1 — Important (after golden path):** env-tunable JWT TTL/rate-limit, appointments UI, patient create form, ARIA overview tabs, meds/allergies editing UI, chart arrow-key navigation, Playwright golden-path E2E + axe scan, role-wired gateway routes, viewport 390px + chart/list toggle polish.
- **P2 — Future:** refresh-token rotation/revocation, audit middleware ordering, clinic-scope hardening on update/delete, framework migration (React/Vite), Redis-backed rate limiting, LLM-backed assistant, dark mode, i18n. **Server-side role enforcement (`requireRole`/`patient_access`) is a documented P2 known limitation** — the P0 gates that UI requires are client-side UX-only guards.

**Non-goals (this MVP):** Redis usage, LLM-backed assistant (rule-based retained), billing/front-desk/generic EHR, dark mode, i18n, sub-390px viewports, more than one golden-path E2E spec. **Global "today's schedule" dashboard panel** — no such aggregate API exists (appointments are patient-scoped) → deferred to P1 with the appointments UI rather than faked.

## Capability matrix (8 MVP capabilities → implementation)

| # | Capability | Frontend entry | Backend source (verified) | P0 task | Acceptance (from 07) |
|---|---|---|---|---|---|
| 0 | Demo-data seed (prerequisite) | — (data, not UI) | allergies/meds/history/chart events/patient↔drug INSERTs for John+Maria | T-1.5 | Every data-bearing demo step has data on a cold stack |
| 1 | Dashboard | `dashboard.js` (role-aware) | `GET /api/patients` (recent) | T-2.3 | Live dashboard, no dead cards |
| 2 | Patient discovery | `patients.js` (search) | `GET /api/patients?search=` | T-2.1 | "john"→John Smith |
| 3 | Patient overview + context | `patient-overview.js` (persistent header) | patients + `patient_history` (allergies/meds) | T-2.2 | Banner identity/alerts pinned |
| 4 | Dental chart | `odontogram.js` + `dental-chart.js` | `GET/POST .../dental-chart` + tooth events | T-3.1/3.2 | All teeth keyboard-reachable; event persists |
| 5 | Orthopedic chart | `skeleton-svg.js` + `skeleton.js` | `GET/POST .../skeleton` + bone events | T-4.1/4.2 | Region→bone; worst-state visible |
| 6 | Medication check | `drug-checker.js` | `POST /api/drug-interactions/check` (preseeded) | T-5.1 | Major interaction w/ source+evidence; honest no-result |
| 7 | Patient assistant | `ai-assistant.js` | `POST /api/chat/patient` (rule-based + RAG) | T-5.2 | Citations + missing-info + banner |
| 8 | Appointments & activity | `appointments.js` + timeline | `CRUD /api/patients/{id}/appointments` + events | T-6.5 (P1/stretch) | Deferred to P1; record persists end-to-end |

## Role capability map

| Capability | Dentist (seeded) | Orthopedist (seeded) | Admin (P1 seed) |
|---|---|---|---|
| Patient search / overview | ✅ | ✅ | ✅ |
| Dental chart + events | ✅ | ❌ (route-guarded) | ✅ |
| Orthopedic chart + events | ❌ (route-guarded) | ✅ | ✅ |
| Medication check | ✅ | ✅ | ✅ |
| Assistant | ✅ | ✅ | ✅ |
| Appointments | P1 | P1 | ✅ |
Server-side `requireRole`/`patient_access` not yet enforced (P2, documented) — client guards are demo-accurate UX only.

## Demo story (one sentence)

> A clinician logs in (Dr. Sarah Chen, dentist) → the dashboard surfaces recent patients and role-aware shortcuts → finds synthetic patient John Smith → the patient banner keeps identity, allergies, medications, and warnings visible → reviews and records a dental finding, then hands off to Dr. James Wilson (orthopedist) for an orthopedic finding → checks a medication pair for interactions → asks the assistant a patient-specific question (answer + citations + missing info + disclaimer) → sees a clear activity trail.

## Success metrics

- Cold-start demo: `docker compose down -v && docker compose up --build` → documented credentials work → golden path runs end-to-end with **no undocumented manual fixes** (acceptance criterion 18)
- No uncaught console errors in primary journeys
- All P0 interactive controls keyboard-operable; WCAG 2.2 AA contrast; states never communicated by color alone
- Lighthouse a11y ≥ 90 on primary screens (where appropriate) — as a floor, not a substitute for keyboard/SR review
- Every quality gate passes with recorded evidence (see `11-quality-gate-scorecard.md`)
- A reviewer unfamiliar with the implementation can follow `10-demo-script.md` end-to-end with no dead ends