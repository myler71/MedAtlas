# UI Redesign — Planning Deliverables

Planning artifacts for the Clinical Care Workspace UI/UX MVP. Produced during the planning phase only — **no implementation happens until the explicit Milestone 1 approval gate is passed.**

**Source of truth for the underlying system:** [`../technical-analysis/`](../technical-analysis/) (SYSTEM_OVERVIEW, DATA_STRUCTURES, DATA_FLOW, KEY_FUNCTIONS, KEY_QUESTIONS) + verified repository inspection (see `00-current-state-audit.md`).

## Index

| # | Document | Purpose |
|---|---|---|
| 00 | [`00-current-state-audit.md`](00-current-state-audit.md) | Verified architecture, frontend/backend inventory, API-to-screen map, reusable assets, broken/missing areas |
| 01 | [`01-product-brief.md`](01-product-brief.md) | Product vision, personas, jobs to be done, MVP scope, non-goals, demo story, success metrics |
| 02 | [`02-information-architecture.md`](02-information-architecture.md) | Sitemap/navigation, patient workspace structure, key user flows, screen-by-screen content hierarchy |
| 03 | [`03-design-system.md`](03-design-system.md) | Visual direction, design tokens, component inventory + states, accessibility and chart-legend rules |
| 04 | [`04-frontend-architecture.md`](04-frontend-architecture.md) | Options comparison, recommended approach (ADR), routing/state/API/forms/errors/testing/migration strategy |
| 05 | [`05-implementation-plan.md`](05-implementation-plan.md) | Phased plan with dependencies, milestones, risks, relative effort, approval gates; tasks in the required format |
| 06 | [`06-agent-workplan.md`](06-agent-workplan.md) | Agent/subagent roles, responsibilities, inputs/outputs, allowed files, handoff/merge procedure |
| 07 | [`07-acceptance-test-plan.md`](07-acceptance-test-plan.md) | Test matrix, user-journey acceptance scenarios, accessibility checks, visual regression, failure scenarios |
| 08 | [`08-decision-log.md`](08-decision-log.md) | Confirmed decisions, assumptions, open questions, deferred work |
| 09 | [`09-architecture-extension-guide.md`](09-architecture-extension-guide.md) | How to add a module, role, route, API integration, design-system component, or nav entry without rework |
| 10 | [`10-demo-script.md`](10-demo-script.md) | Timed 5–10 minute golden-path presentation using synthetic data |
| 11 | [`11-quality-gate-scorecard.md`](11-quality-gate-scorecard.md) | Product/UX/UI/engineering/a11y/responsive/reliability/clinical-safety/demo gates with evidence rules |
| v | [`verification.md`](verification.md) | Per-gate evidence record (commands, outputs/SHA, screenshots, sign-off) populated during M1–M6 |

Wireframes: [`wireframes/00-all-screens.md`](wireframes/00-all-screens.md) — low-fidelity textual wireframes for the global shell/dashboard, patient list, patient overview, dental workspace, orthopedic workspace, medication interaction checker, and patient assistant.

## Related docs

- Master prompt for this engagement: `C:\Users\Myler\Downloads\claude-code-clinical-platform-prompt (1).md`
- Exported execution plan: `C:\Users\Myler\Downloads\1 PROJECTS\clinical-platform-uiux-mvp-execution-plan.md`