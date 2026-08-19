# 04 — Frontend Architecture

## Options comparison

| Criterion | A: Vanilla + hash router (build-less) | B: React/Vue + Vite | C: Staged hybrid |
|---|---|---|---|
| Time-to-MVP (days) | **Best** — no toolchain setup | Worst — 2–4 day migration before new UX | ≈A + dual-paradigm tax |
| Visual/interaction ceiling | High for this scope (8 screens, tables/tabs/drawers/2 SVG charts) | Highest long-term | Mixed |
| Maintainability | Good at ~1.1k LOC, class-per-page convention | Best long-term | Worst (two mental models) |
| Risk to working flows | **Minimal** — reuse both chart classes | High — both rewritten | Medium |
| Testability | Playwright + axe are framework-agnostic | Best (Testing Library) | Medium |
| A11y tooling | axe via Playwright + manual keyboard walkthroughs — sufficient for AA here | Best-in-class linting | Medium |
| Build complexity | **Zero** — Express static untouched | New build in every deploy path | Partial |
| Chart migration cost | **Zero** | Full SVG rewrite | Half |

## Decision (ADR)

**Build-less componentized ES-module frontend + hash router for the MVP. Framework migration explicitly deferred: post-MVP, contingent on the app growing beyond ~30 components or needing rich data-grid/calendar primitives.**

The deciding factor is the rewrite-to-reuse ratio against a hard days deadline. The frontend is 18 files / ~1.1k LOC; the two highest-risk assets (odontogram, skeleton) are already isolated class components with stable APIs — reuse 100% of the working clinical logic and spend the budget on the actual gaps (navigation, discovery, states, a11y, polish). A framework tax of 2–4 migration days produces zero visible UX improvement at this scope and maximizes regression risk on the only flows that work today. Option C is Option A plus a promise — rejected. Quality gates (WCAG 2.2 AA, keyboard, states-not-color-only, responsive fallbacks) require discipline, not a framework; a frozen component inventory provides that discipline.

**Rollback:** all changes are additive to the Express static-serving path; the SPA fallback already exists. Any milestone can be reverted by `git revert` of the feature-branch commits; the old linear app flow remains on `master`.

## Module structure (delta view)

```
frontend/
  index.html                  MOD  link dental.css + skeleton.css; skip-link; <div id="shell"> + <main id="view">
  css/
    variables.css             MOD  extended tokens (focus-ring, type scale, semantic state colors, z-index, breakpoints)
    layout.css                MOD  app-shell grid, container widths, responsive rules
    components.css            MOD  expand to full kit (see 03-design-system.md §components)
    charts.css                NEW  shared chart chrome: legend, focus-visible, list-alternative, chart/list toggle
    dental.css                MOD  keep state classes; add focus styles + alt-list hooks
    skeleton.css              MOD  same
  js/
    api.js                    REW  ApiError{status,code,message}; 401→clearSession+navigate('#/login?expired=1');
                                   API_BASE=location.origin; safe JSON parse; normalized errors
    auth.js                   NEW  session store (localStorage 'clinical.session' {token,user{id,role,full_name}});
                                   getSession/login/logout/hasRole; change events for shell
    router.js                 NEW  hash router: route table, guards, navigate(), hashchange, active-link, focus main (~<150 LOC)
    app.js                    REW  bootstrap: mount shell, register routes, start router (~25 lines)
    shell.js                  NEW  AppShell: topbar, nav filtered by role, patient context bar, breadcrumbs
    components/
      odontogram.js           MOD  native-button tooth wrapping, aria-labels, legend hooks, list alternative (API unchanged)
      skeleton-svg.js         MOD  same pattern
      state-legend.js         NEW  shared legend: shape+label per state — never color-only
      drawer.js               NEW  role=dialog, focus trap, Esc, backdrop, focus restore
      toast.js                NEW  aria-live region
      states.js               NEW  skeletonLoader()/emptyState()/errorState({retry}) partials
      table.js                NEW  thead/tbody helper + responsive card transform + optional sort
      tabs.js                 NEW  ARIA tablist, arrow-key roving (M2/P1)
    pages/
      login.js                NEW  merged role segmented control + sign-in/register (replaces role-selection.js + auth.js)
      dashboard.js            REW  live counts + quick actions (no dead cards)
      patients.js             NEW  searchable patient list (server-side ?search=)
      patient-overview.js     REW  route-driven; summary cards; meds/allergies/history; recent events; entries to charts
      dental-chart.js         MOD  fit shell; drawer for tooth detail/events; keep data flow
      skeleton.js             MOD  same
      drug-checker.js         MOD  wire to route; labelled chips; severity badges icon+text+color; prefill ?patient=
      ai-assistant.js         MOD  wire to route; decision-support banner; keep citation rendering
      appointments.js         NEW  P1/stretch: list + book form (backend CRUD exists)
```

## Key decisions

- **Routing:** hash router (`#/`), flat route table, role guards. Zero backend change (SPA fallback already in `server.js`).
- **Patient context:** `patientId` in the URL hash — deep links, back/forward, fresh tabs all work; no cross-tab state sync problem. Optional in-memory TTL cache (P1).
- **Session/state:** module-scope session store over localStorage; no state library (YAGNI at this size).
- **API client:** single choke point for 401 → redirect to login with toast; normalized `ApiError`; base URL from `location.origin`.
- **SVG a11y:** native `<button>` wrapping for teeth (free Tab/Enter/Space/focus ring), `role="button" tabindex="0"` + Enter/Space for region paths; always-on text list alternative.
- **Forms:** native validation + inline errors; disabled submit while pending; no form library.
- **Loading/optimistic:** skeleton loaders on data reads; POST events use pending-disable + success toast + in-place chart refresh (no optimistic mutation that could lie about persisted state).
- **CSS:** token-first; extend existing variables.css; chart chrome separate from page styles.
- **Testing:** pure modules (router, api, state maps) Node-testable; Playwright golden-path E2E + axe (P1/stretch); manual keyboard/SR walkthroughs every milestone.
- **Seeding/demo:** declarative compose initdb mounts (M1) + real bcrypt seed hashes + documented `docker compose down -v` reset; demo role selector explicitly labeled demo-only.
- **Backend changes mandatory for P0: exactly 3** — real seed hashes, compose initdb mounts, README quick-start. Zero API contract changes. Everything else backend is P1/P2 (see `08-decision-log.md`).