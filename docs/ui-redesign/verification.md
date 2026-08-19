# Verification Evidence

Per-gate evidence record for the **Clinical Platform UI/UX MVP** (see `05-implementation-plan.md` gates and `11-quality-gate-scorecard.md`). A gate is **green** only when the exit criteria rows below have recorded evidence (commands, outputs, SHAs, screenshots, reviewer sign-off). No row is filled retroactively by memory — rerun or cite the run.

> Template status: 🟡 in progress. Milestones M1–M6 populate rows as they land; final sign-off happens at the M6 quality gate.

## How to run the golden path (source of truth: `10-demo-script.md`)

```powershell
docker compose down -v
docker compose up --build -d
curl.exe -s http://localhost:3000/api/health
```

Seeded credentials (M1): `dentist@clinic.com` / `password123` (Dr. Sarah Chen), `ortho@clinic.com` / `password123` (Dr. James Wilson). No admin user is seeded (P1).

## Gates (numbering matches `05-implementation-plan.md`)

### G0 — Plan approval

| Check | Evidence |
|---|---|
| Plan (`05`) + spec set (`docs/ui-redesign/` 00–11 + wireframes + verification template) written and internally consistent | committed paths; critic review pass done |
| User approved plan + spec set | approval note (date) |

### G1 — Spec review

| Check | Evidence |
|---|---|
| Independent critic review of the doc set — no BLOCKERs/REQUIREDs outstanding | critic findings log + resolution |
| Final A–J readout + Milestone-1 approval gate issued (master prompt §13 J) | readout record (date) |

Then per milestone: **M1 → G2 · M2 → G3 · M3 → G4 · M4 → G5 · M5 → G6 · M6 → G7**.

### G2–G6 — Milestone gates (M1…M5)

Record per milestone: commands run + output (paste behind fenced code blocks), key file SHAs, UI screenshots at 1280/820, reviewer sign-off (agent + date).

| Gate | M | DoD (from 05) | Commands | Output/SHA | Screenshots | Sign-off |
|---|---|---|---|---|---|---|
| G2 | M1 Foundation | cold stack → curl-verified login; shell+dashboard; 401 redirect; dental.css 200 | | | | |
| G3 | M2 Discovery | search "john"→John Smith; deep link `#/patients/:id`; role-gated nav | | | | |
| G4 | M3 Dental | tab to all 32 teeth; Enter opens drawer; Esc restores focus; event-add updates in place; 9-state legend w/ text | | | | |
| G5 | M4 Ortho | mirror M3; worst-state visible in labels/legend/list | | | | |
| G6 | M5 Meds+assistant | warfarin+aspirin → major w/ source+evidence (from demo seed); no-result caveat verbatim; citations+missing-info; keyboard-operable | | | | |

### G7 — Quality gates (M6 outcome; owner per `11`)

| Gate | Evidence recorded | Status |
|---|---|---|
| Product | golden path solves coherent problem in verified capabilities; non-goals respected | 🔴 |
| UX | walkthrough: discovery + recovery unaided | 🔴 |
| UI | screenshot set at 1280/820; no default-browser experiences | 🔴 |
| Engineering | ADR (04) matches implementation; extension seams (09) match reality | 🔴 |
| Accessibility | keyboard journey; focus semantics; AA contrast; non-color states; axe (where runnable) | 🔴 |
| Responsive | 1280 + 820 usable (P0); chart/table alternatives at small widths | 🔴 |
| Reliability | failure-mode checklist (07) executed on P0 screens | 🔴 |
| Clinical safety | assistant banner + citations + missing-info; no misleading affordances | 🔴 |
| Demo | 5–10 min script from cold stack; no dead ends; fallbacks work | 🔴 |

## Known limitations (carry forward, do not hide)

- Refresh-token rotation/revocation incomplete (P2) — 401 choke point in `api.js` covers expiry gracefully (M1).
- In-memory rate limit (100/15m) — avoid rapid-fire page loads during demo; P1 env-tunable.
- Client-side role guards are UX only; server-side `requireRole`/`patient_access` enforcement is P2 (documented).
- Seeded users may not log in on a cold stack until M1/T-1.1 lands (placeholder hashes in `database/seed.sql`).

## Sign-off

| Role | Name/Agent | Date | Note |
|---|---|---|---|
| Product/UX lead | | | |
| Architect | | | |
| A11y reviewer | | | |
| Security/clinical-safety | | | |
| QA lead | | | |
| Final approval | | | |