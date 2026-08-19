# 01 — Product Brief

## Product vision

A **Clinical Care Workspace**: a calm, trustworthy, information-dense application in which a dentist or orthopedist can log in, find a patient, understand the patient's important context in under 30 seconds, document a dental or orthopedic finding, inspect medications and allergies, check interactions, and ask the patient-scoped assistant a question without losing context.

Deliver a polished, accessible, demo-ready workspace that moves from patient discovery to anatomical charting, medication safety review, and evidence-backed patient assistance in one coherent, safe, role-aware workflow.

## Personas & jobs to be done

| Persona | Primary jobs | Demo-critical moments |
|---|---|---|
| **Dentist** | Find patient → review allergies/meds → read/sign a tooth chart → record an event | Tooth selection, state legend, event capture, keyboard use |
| **Orthopedist** | Find patient → review context → read region/bone findings → record an event | Region/bone selection, worst-state visibility |
| **Admin** | Broad visibility across both disciplines; role-gated navigation | Role-gating is demo-accurate, not decorative |

Model only what the codebase supports. Do not invent front-desk, billing, or insurance personas.

## MVP scope

- **P0 — Essential (golden path):** seeded loginable stack; hash router + app shell; patient list/search → patient overview → dental chart → skeleton chart → medication checker → assistant; persistent patient header; loading/empty/error/permission states; keyboard + non-color accessibility; honest decision-support framing.
- **P1 — Important (after golden path):** env-tunable JWT TTL/rate-limit, appointments UI, patient create form, ARIA overview tabs, meds/allergies editing UI, chart arrow-key navigation, Playwright golden-path E2E + axe scan, role-wired gateway routes.
- **P2 — Future:** refresh-token rotation/revocation, audit middleware ordering, clinic-scope hardening on update/delete, framework migration (React/Vite), Redis-backed rate limiting, LLM-backed assistant, dark mode, i18n.

**Non-goals (this MVP):** Redis usage, LLM-backed assistant (rule-based retained), billing/front-desk/generic EHR, dark mode, i18n, sub-390px viewports, more than one golden-path E2E spec.

## Demo story (one sentence)

> A clinician logs in → the dashboard shows today's work → finds a synthetic demo patient → the patient banner keeps identity, allergies, medications, and warnings visible → reviews and records a dental and an orthopedic finding → checks a medication pair for interactions → asks the assistant a patient-specific question (answer + citations + missing info + disclaimer) → sees a clear activity trail.

## Success metrics

- Cold-start demo: `docker compose down -v && docker compose up --build` → documented credentials work → golden path runs end-to-end with **no undocumented manual fixes** (acceptance criterion 18)
- No uncaught console errors in primary journeys
- All P0 interactive controls keyboard-operable; WCAG 2.2 AA contrast; states never communicated by color alone
- Lighthouse a11y ≥ 90 on primary screens (where appropriate) — as a floor, not a substitute for keyboard/SR review
- Every quality gate passes with recorded evidence (see `11-quality-gate-scorecard.md`)
- A reviewer unfamiliar with the implementation can follow `10-demo-script.md` end-to-end with no dead ends