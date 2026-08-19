# 08 — Decision Log

## Confirmed decisions

| # | Decision | Rationale | Recorded |
|---|---|---|---|
| D1 | **Frontend approach A** — build-less componentized Vanilla JS + hash router | Rewrite-to-reuse ratio vs. hard days-timeline; charts already componentized; zero-build deploy path | `04-frontend-architecture.md` (ADR) |
| D2 | Framework migration (React/Vite) deferred to post-MVP | Not binding for the scope's quality gates; would burn 2–4 days for no visible UX gain | `04` |
| D3 | Patient scope via URL hash (`#/patients/:id`) | Deep links, back/forward, fresh tabs, independent role-gated chart pages, no cross-tab cache-invalidation | `04` |
| D4 | Session in localStorage + module-scope store; no state library | Small enough scope; YAGNI | `04` |
| D5 | 401 handled in one place in `api.js` → clear + redirect + toast | Single choke point for expiry (no refresh endpoint exists) | `04` |
| D6 | Native `<button>` wrapping for SVG teeth / `role=button` for region paths; always-on text list alternative | Keyboard + SR semantics for free; avoids custom widget risk; list-alt doubles as small-screen view | `03`, `04` |
| D7 | Frozen component inventory; add abstractions only via ADR note | Bounds Vanilla scope creep | `03` |
| D8 | **Backend changes for P0 = exactly 3** (seed hashes, compose initdb mounts, README); zero API contract changes | Keep "UI redesign" from becoming a backend rewrite; demo must boot from cold stack | `05` |
| D9 | Drug-checker "no interaction found ≠ safe" wording preserved verbatim | DB is pre-seeded-only; never imply safety from absence of a match | `05` |
| D10 | Assistant flagged as decision-support with persistent banner; rule-based (no LLM) is the honest truth | Clinical-safety gate | `05` |
| D11 | Demo role selector (client-side) labeled demo-only; real auth server-driven | Never treat client role selection as authorization | `02`, `04` |
| D12 | Light theme baseline; dark mode optional/non-blocking | Master prompt §7 | `03` |

## Assumptions

- Docker Desktop + full stack is available locally for verification (user-confirmed).
- Audience: clinical/technical stakeholders, coursework/capstone, portfolio → credibility, docs coverage, and polish all matter.
- Timeline: ASAP/days → P0 golden path only; P1 items follow only if they don't delay the golden path.
- The uncommitted changes in the repo (`server.js`, `requirements.txt`, untracked `docs/`, `graphify-out/`) are the user's own work-in-progress — **must not be disturbed**; implementation happens on a feature branch.
- `pgvector/pgvector:pg16` and `redis:7-alpine` images pull successfully on the demo machine (unverified until M1).
- Tavily/RxNorm external services may be unavailable at demo time → assistant and drug resolve must degrade gracefully (failure states are P0).

## Open questions

1. Are the seeded demo emails/roles (`dentist@clinic.com`, `orthopedist@clinic.com`, `admin@clinic.com` — confirm from `seed.sql`) the intended demo credentials? (Default assumption: yes, password `password123`.)
2. Should the access-token expiry be raised via env for demo recordings? (P1; default unchanged 15m.)
3. Is Playwright available for a golden-path E2E, or do we rely on the documented manual walkthrough? (Probed at implementation start.)

## Deferred (with rationale)

- **Refresh rotation/revocation, audit ordering, clinic-scope hardening** (P2) — real production hardening; out of MVP demo scope; documented as known limitations, not hidden.
- **Redis adoption or decommission** — unused today; leaving as-is, unchanged for MVP.
- **LLM-backed assistant** — rule-based synthesis retained; documented and framed honestly.
- **Appointments UI** — backend CRUD exists; P1/stretch.
- **Dark mode, i18n, sub-390px** — non-goals.