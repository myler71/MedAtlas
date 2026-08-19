# 02 — Information Architecture

## Navigation / sitemap (hash router)

| Hash route | Guard | Page |
|---|---|---|
| `#/login` | guest | Login (merged role selector + sign-in/register) |
| `#/` alias `#/dashboard` | auth | Dashboard |
| `#/patients` | auth | Patient list/search |
| `#/patients/:id` | auth | Patient overview |
| `#/patients/:id/dental` | auth + role dentist\|admin | Dental chart |
| `#/patients/:id/skeleton` | auth + role orthopedist\|admin | Skeleton chart |
| `#/patients/:id/assistant` | auth | AI assistant |
| `#/drug-checker` | auth | Drug interaction checker |
| `#/appointments` | auth (P1) | Appointments |

**Role-gating is demo-accurate:** names the capabilities the backend actually scopes. Real authorization stays server-driven (header-based clinic/role); client-side guards are UX only. Role capability map: `01-product-brief.md` §Role capability map. Admin is in the schema but **not seeded** (P1) — no fake admin login in the demo.

## Wireframe values are illustrative

Screen values in `wireframes/00-all-screens.md` (names, phonetimes, dates beyond the two seeded patients) are layout examples, not data promises. The only guaranteed demo data is the seed set verified in `00-current-state-audit.md` §Seeded synthetic data.

## Global shell

Persistent: brand + clinic identity, primary nav (dashboard, patients, drug checker — filtered by role), current user + role badge, sign-out. On patient routes, a **patient context bar** shows identity, allergies, active meds, and high-priority warnings; its width collapses to a banner on smaller screens. Breadcrumbs on deep pages (`Patients › Smith, John › Dental chart`).

## Patient workspace

One stable patient context across tabs: **Overview · Dental chart · Orthopedic chart · Medications/Allergies/History · Appointments (P1) · Assistant**. `patientId` lives in the URL hash so deep links, back/forward, and fresh tabs preserve context. No duplicated patient data across pages — the shell's patient header is the single source of identity.

## Key user flows

### Golden path (P0)
1. Guest → login (`demo-role` selector labeled demo-only; server enforces real auth) → dashboard.
2. Dashboard: recent patients (live `GET /api/patients`) + role-aware shortcuts + actionable alerts only where data supports them. **No "today's queue" panel in P0** — no aggregate schedule API exists (appointments are patient-scoped); that panel is P1 with the appointments UI.
3. Global/patient search → patient list → open patient.
4. Patient overview: summary cards + meds/allergies/history + recent events + entry buttons to charts/assistant.
5. Dental chart: tooth states from `GET .../dental-chart`; click/tab a tooth → drawer with state + history + Add Event (POST). Legend always visible.
6. Skeleton chart: same pattern via `GET .../skeleton`; region → bones; worst-state surfaces by priority.
7. Drug checker: search/resolve meds, pick a pair → interaction result with severity/evidence/missing-drug states.
8. Assistant: patient context visible; question → answer + citations + missing info + safety banner.

### Workflow-state coverage (P0+p1)
Every flow documents: entry point, screens, primary/secondary action, data + source API, **success / loading / empty / validation / error / unauthorized / forbidden / unavailable-service states** (see `07-acceptance-test-plan.md`).

## Screen-by-screen content hierarchy

**Dashboard** — Recent patients (from `GET /api/patients`) · Role-aware shortcuts · Alerts (actionable only, if derivable) · Quick actions. No decorative stats; **no invented today-queue panel** (P1, see above).
**Patient list** — Search (debounced, server-side `?search=`), filter/sort, keyboard rows, pagination or incremental loading as supported.
**Patient overview** — Identity + warnings (banner) · Meds · Allergies · Medical history · Recent events · Quick actions.
**Dental workspace** — Chart (primary) · Legend (never color-only) · List alternative · Details drawer (state + history + event entry).
**Orthopedic workspace** — Body/regions chart (primary) · Region list alternative · Details drawer.
**Medication interaction** — Med list (active/discontinued) · Allergy context · Resolve/search · Pair check results (severity, mechanism, source, evidence) · accurate no-result wording.
**Assistant** — Patient context pinned · Answer, evidence/citations, missing information, safety note as separate sections · starter questions.