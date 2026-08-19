# 10 — Demo Script (5–10 min, synthetic data)

**Personas — both are the *actually seeded* users (no invented identities):**
- **Dr. Sarah Chen** — dentist, `dentist@clinic.com` / `password123`
- **Dr. James Wilson** — orthopedist, `ortho@clinic.com` / `password123`

Demo-verified patients: **John Smith** (1984-03-15, 555-0201) and **Maria Garcia** (1992-07-22, 555-0202) — see `00-current-state-audit.md` §Seeded synthetic data. No admin account is seeded (P1); the demo never presents a fake admin.

**Data prerequisite (P0, M1):** the seeded users/patients exist in `seed.sql`, but the demo's **clinical content** (John's penicillin allergy, active warfarin+aspirin, prior chart events, assistant INR context) is **not part of the current seed** — it is created by the new `database/seeds/demo_clinical.sql` (T-1.5), which must mirror this script exactly. Until T-1.5 lands, steps 4–9 below have no data source; this script is the contract that T-1.5 seeds against.

**Prerequisites:** fresh stack seeded via `docker compose down -v && docker compose up --build`; login at `http://localhost:3000`.

| # | Time | Action | Expected on screen | Talking points |
|---|---|---|---|---|
| 1 | 0:00 | Open `http://localhost:3000`, sign in as **Dr. Chen** | Clean login; role selector labeled demo-only | "One-click demo environment; production auth is server-side." |
| 2 | 0:20 | Dashboard | Recent patients, role-aware shortcuts — **live data, no dead cards** | "Role-aware dashboard opens today's work: recent patients and direct chart access." |
| 3 | 0:45 | Search patient "smith" → open | Patient list → **John Smith** overview | "Patient context in under 30 seconds." |
| 4 | 1:15 | Review patient banner | Identity (John Smith, 1984-03-15), allergies, active meds, warnings pinned across the workspace | "Critical context stays visible everywhere." |
| 5 | 1:45 | Open **Dental chart**; select a tooth | Tooth states + legend (shape+text), details drawer with history | "Keyboard-operable teeth; events recorded to the real API." Record one event (e.g. caries → restoration). |
| 6 | 2:45 | **Handoff:** sign out, sign in as **Dr. Wilson** (orthopedist), reopen John Smith | Skeleton chart now reachable (role-gated); dental chart hidden from ortho nav | "Cross-disciplinary handoff — each role sees only its routes. The guard is client-side UX for now; real server-side role enforcement is a documented P2 limitation (we never claim otherwise)." |
| 7 | 3:45 | Open **Skeleton chart**; select a region | Region/bone findings, worst-state priority, drawer | "Orthopedic workflow first-class; same chart pattern." Record one event. |
| 8 | 4:45 | **Drug checker**: warfarin + aspirin | Major interaction with severity, source, evidence | "Preseeded pair; note the honest 'no result ≠ safe' wording for anything else." |
| 9 | 5:30 | **Assistant**: patient-scoped question | Answer + citations + missing-info + decision-support banner | "Rule-based synthesis of the patient record, with sources and clear safety framing." |
| 10 | 6:15 | Back to patient overview | New events visible; the record now reflects the documentation | "Complete, persistent audit trail across both roles." |
| 11 | 7:00 | Debrief | — | Non-goals & honest limitations: preseeded-only interactions, no LLM, no refresh rotation, role gating is client-side UX (server-side enforcement is P2, documented). |

**Route-gating note (honest, not a glitch):** the UI hides cross-role routes and blocks direct navigation, but this is **client-side UX only** — the gateway/FastAPI do not yet enforce roles (`requireRole`/`patient_access` wired is P2). We demo the handoff rather than a single omnipotent role and never claim server-side enforcement. Admin exists in schema only; no admin login is demonstrated.

**Fallbacks:** if Tavily/RxNorm unavailable → assistant and drug resolve show degraded-service states (designed, not broken). If JWT expires mid-demo → auto-redirect to login with toast (graceful). Avoid rapid-fire repetition of page loads (in-memory rate limit 100/15m).

**Prereq check:** run `curl.exe -s http://localhost:3000/api/health` before starting; verify both health endpoints green. Confirm seeded users log in (`POST /api/auth/login` with the credentials above) — M1/T-1.1 makes this true from a cold stack.