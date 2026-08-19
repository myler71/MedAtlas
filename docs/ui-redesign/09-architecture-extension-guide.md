# 09 — Architecture Extension Guide

How to grow the platform without rework. **Current extension seams (verifiable now)** are marked ✅; **future recommendations** marked 🔜 (post-MVP).

## Add a clinical module/feature

1. ✅ **New page:** add a route to the router table (`js/router.js`), create `js/pages/<name>.js` exporting a class with `mount(container, {params, api})`; register in `shell.js` nav (if not patient-scoped) or the patient context bar (if patient-scoped).
2. ✅ **New component:** add to `frontend/js/components/` and the CSS inventory; must document default/hover/focus/selected/disabled/loading/error states; never color-only.
3. ✅ **New API integration:** add the call through `js/api.js` (single fetch/error surface); document the endpoint in the API-to-screen map (`00`); do not bypass `ApiError` normalization.
4. 🔜 **Backend module:** register a router in `backend/fastapi/app/main.py`, add a numbered migration in `database/migrations/`, and wire the seed file into compose initdb mounts. Follow existing patterns (raw SQL + derived-state mapping, clinic scoping on reads).
5. 🔜 **New specialty (e.g. radiology):** mirror the dental/orthopedic pattern: chart tables + events migration, chart component + page + legend, role guard in the router table, seeded synthetic scenario.

## Add a role

1. ✅ Client: add the role to the login role options (labeled demo-only) and to the router table guard checks (`hasRole`).
2. ✅ Verify what the role can actually do **server-side**; client-side guards are UX only.
3. 🔜 Real enforcement: wire `requireRole` (`backend/express/src/middleware/rbac.js`) onto the gateway proxy routes, and add `patient_access` enforcement at the route level (currently table-only).
4. 🔜 Seed: add the role + demo user in `database/seed.sql` with real bcrypt hash, and a matching demo-script persona.

## Add a route

- Add hash route to `js/router.js` with `{path, page, guard}` semantics. Deep pages take `:params`. Focus management: route change focuses `#main`; keep breadcrumbs consistent (patient context bar helper in `shell.js`).

## Add design-system tokens/components

- Remove/change tokens only in one of: `css/variables.css` (tokens), `css/layout.css` (shell/grid), `css/components.css` (kit), `css/charts.css` (chart chrome). Page-specific styles stay in page CSS (`dental.css`, `skeleton.css`). Add new components to the frozen inventory only with an ADR note (`08`).

## Add navigation entry

- Global nav: `shell.js` (filtered by role). Patient-scoped entries: patient context bar. Deep actions: dashboard quick actions → router navigate. Keep "active" state synced via router events.

## Add an integration with an external service (e.g., new retrieval source)

- `backend/fastapi/app/rag/` — add behind the existing retriever interface; keep local evidence separation from external web evidence visible in the assistant payload (`citations`/`missing_information`); degrade gracefully when the external service is down; demo fallback documented in `10-demo-script.md`.

## Guardrails

- Do not change Express→FastAPI trust headers without an approved, documented reason.
- Do not change public API contracts without documenting reason, affected clients, migration path, and approval.
- New demo/synthetic data only; never real PHI. Keep seed data clearly labeled synthetic.
- Effects on the **quality gates** (`11`) must be reviewed before adopting any architectural change.