# 10 — Demo Script (5–10 min, synthetic data)

**Persona:** Dr. Aisha Rahman, dentist (synthetic). **Prerequisites:** fresh stack seeded via `docker compose down -v && docker compose up --build`; login at `http://localhost:3000`.

| # | Time | Action | Expected on screen | Talking points |
|---|---|---|---|---|
| 1 | 0:00 | Open `http://localhost:3000`, sign in as dentist | Clean login; role selector labeled demo-only | "One-click demo environment; production auth is server-side." |
| 2 | 0:20 | Dashboard | Today's appointments/queue, recent patients, role shortcuts — **live data, no dead cards** | "Role-aware dashboard frames today's work." |
| 3 | 0:45 | Search patient (e.g. "Smith") → open | Patient list → John Smith overview | "Patient context in under 30 seconds." |
| 4 | 1:15 | Review patient banner | Identity, allergies, active meds, warnings pinned across the workspace | "Critical context stays visible everywhere." |
| 5 | 1:45 | Open **Dental chart**; select a tooth | Tooth states + legend (shape+text), details drawer with history | "Keyboard-operable teeth; events recorded to the real API." Record one event (e.g. caries → restoration). |
| 6 | 2:45 | Open **Skeleton chart**; select a region | Region/bone findings, worst-state priority, drawer | "Orthopedic workflow first-class; same chart pattern." Record one event. |
| 7 | 3:45 | **Drug checker**: warfarin + aspirin | Major interaction with severity, source, evidence | "Preseeded pair; note the honest 'no result ≠ safe' wording for anything else." |
| 8 | 4:30 | **Assistant**: patient-scoped question | Answer + citations + missing-info + decision-support banner | "Rule-based synthesis of the patient record, with sources and clear safety framing." |
| 9 | 5:15 | Back to patient overview | New events visible; the record now reflects the documentation | "Complete, persistent audit trail." |
| 10 | 5:45 | Debrief | — | Non-goals & honest limitations: preseeded-only interactions, no LLM, no refresh rotation, role gating is demo-accurate. |

**Fallbacks:** if Tavily/RxNorm unavailable → assistant and drug resolve show degraded-service states (designed, not broken). If JWT expires mid-demo → auto-redirect to login with toast (graceful). Avoid rapid-fire repetition of page loads (in-memory rate limit 100/15m).

**Prereq check:** run `curl.exe -s http://localhost:3000/api/health` before starting; verify both health endpoints green.