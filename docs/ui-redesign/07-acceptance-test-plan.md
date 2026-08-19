# 07 — Acceptance Test Plan

## Test matrix

| Layer | Tool | Scope |
|---|---|---|
| Unit | Node (node:test or equivalent, no new deps) | router, api error handling, state maps, legend/list-alternative data transforms |
| Integration | `tests/test-auth-patient.sh` (extend) + curl | auth flow, patients search/CRUD, dental/skeleton GET reflect POSTed events |
| Contract | curl against gateway | every P0 frontend-referenced endpoint returns shaped payloads |
| E2E (stretch/P1) | Playwright if available; else manual scripted walkthrough | golden path; axe serious/critical = 0 per page |
| A11y | keyboard + SR manual walkthrough + axe | WCAG 2.2 AA on P0 journeys |
| Failure modes | curl/DevTools | loading/empty/error/unauthorized/forbidden/not-found/degraded-external-service |

## User-journey acceptance scenarios (map to README acceptance criteria §11)

1. **Cold start** — `docker compose down -v && up --build` → documented credentials → login (crit. 1, 3, 18).
2. **No console errors** — P0 journeys open in clean DevTools (crit. 2).
3. **Patient discovery** — search "john" → John Smith → open → context banner visible (crit. 3, 4).
4. **Dental event** — select tooth → understand state → review events → record one event → state updates in place (crit. 4).
5. **Orthopedic event** — select region/bone → understand state → review events → record one event (crit. 5).
6. **Interaction check** — warfarin + aspirin → major interaction w/ severity+source+evidence; a pair with no record → explicit caveat, never "safe" (crit. 6).
7. **Assistant** — question → answer separated from citations/evidence/missing-info/safety (crit. 7; clinical-safety gate).
8. **Keyboard E2E** — login → search → open patient → both charts → drug check → assistant, all with Tab/Enter/Space; focus visible; dialogs trap/restore (crit. 8, 9).
9. **Contrast/non-color** — text/UI AA; states identifiable without color (crit. 10).
10. **Responsive** — 1280 + 820 usable; complex charts/ tables have documented alternatives (crit. 11).
11. **State coverage** — each P0 screen: loading, empty, validation, error, unauthorized, forbidden, not-found, service-down (crit. 12).
12. **Fresh-checkout fidelity** — docs + demo script reproducible; no manual DB edits (crit. 18); `09-architecture-extension-guide.md` matches implementation (crit. 19); reviewer-independent demo (crit. 20).
13. **Data hygiene** — no real PHI or secrets committed anywhere (crit. 14); new deps/creds/limitations documented (crit. 15); backend contracts unchanged (crit. 16); evidence recorded for completion claims (crit. 17).

## Accessibility checks (each P0 screen)

Keyboard-only operation; visible focus order; screen-reader semantics (roles/labels/names for SVG charts via native buttons + list alternative); dialog focus management; contrast (AA); reduced motion; touch targets ≥ 24px.

## Failure-mode scenarios

401 (expired token) → redirect+toast; 403 (role mismatch) → blocked nav with message; 404 (missing patient) → not-found state; 5xx / network / Tavily-down / RxNorm-down → service-unavailable state with retry; rate-limited → friendly retry-after messaging.