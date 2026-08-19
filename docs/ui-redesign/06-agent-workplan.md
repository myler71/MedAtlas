# 06 — Agent Workplan

## Roles

| Role | Available agent | Responsibilities | Allowed files | Handoff |
|---|---|---|---|---|
| 1. Repository & architecture analyst | `explore` | Map frontend/API/startup/auth; reusable assets; gaps | Read-only | Evidence report with paths |
| 2. Product & clinical UX lead | `analyst` | Personas, journeys, page hierarchy, demo narrative | Read-only + docs | `01`, `02` inputs |
| 3. Design-system & visual lead | `designer` | Tokens, visual direction, components, charts | `docs/ui-redesign/*`, `frontend/css/*` | Token spec + component code |
| 4. Frontend architecture lead | `architect` / `Plan` | Architecture ADR, routing/state/errors | Read-only + `04` | ADR + module delta |
| 5. Backend/API integration engineer | `executor` (+ `explore`) | Verify models/routes/contracts; classify backend change scope | Backend read-only except the 3 P0 data/deploy files | API-to-screen map + change list |
| 6. Accessibility & usability reviewer | `security-reviewer` (a11y focus) | Keyboard/focus/contrast/SR semantics/chart alternatives | Read-only + `03`, `07` | A11y audit per milestone |
| 7. QA & integration lead | `test-engineer`, `qa-tester` | Unit/integration/contract/E2E; acceptance scenarios | `tests/**`, read-only runtime | Test matrix + evidence |
| 8. Security & clinical-safety reviewer | `security-reviewer`, `verifier` | Token handling, PHI exposure, disclaimers, dangerous affordances | Read-only | Risk report (do NOT expand scope unapproved) |

## Delivery flow

- **Discovery (done):** explore x3 parallel → consolidated readout (00).
- **Phase A (this phase):** docs authored directly (evidence held in main context); **critic** agent = separate review lane over the doc set for contradictions/coverage.
- **Phase B (after M1 approval):** per milestone → `executor` implements → `code-reviewer` reviews → `verifier` confirms evidence → gate. `security-reviewer` pass before M6. `qa-tester` walkthrough per DoD; `test-engineer` for M6 acceptance.

## Controls

- Each subagent gets a **narrow brief**, requires **evidence with file paths**, and an **allowed-files** boundary to prevent overlapping edits.
- The lead (main) agent reconciles disagreements into one coherent recommendation.
- No skill/plugin is a hard dependency: Spec Kit is absent → manual equivalents (see `08-decision-log.md`). Superpowers writing-plans/TDD/code-review/verification are available and used. Playwright probed at implementation start; manual browser+checklist fallback if unavailable.

## Future expansion (documented, NOT MVP scope)

Specialists that become useful with growth: billing, interoperability (FHIR), security/compliance, data engineering, DevOps/SRE, clinical informatics, additional specialties (e.g., radiology). Added on a real need basis, not automatically.