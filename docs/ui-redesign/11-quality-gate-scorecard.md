# 11 — Quality Gate Scorecard

Each gate passes only with **recorded evidence**, not a subjective completion claim. Status: 🔴 not started · 🟡 in progress · 🟢 pass · ⛔ blocked.

| Gate | Owner | Evidence required | Status | Blockers | Approval rule |
|---|---|---|---|---|---|
| **Product** | product/UX lead (analyst) | P0 golden path solves a coherent problem within verified capabilities; non-goals respected | 🔴 | — | All P0 acceptance criteria (07) green |
| **UX** | UX lead + qa-tester | New user discovers primary actions & recovers from mistakes unaided (demo-observed) | 🔴 | — | Walkthrough of all journeys |
| **UI** | designer | Visually coherent; no unfinished/default-browser experiences in P0 screens | 🔴 | — | Screenshot set at 1280/820 |
| **Engineering** | architect + code-reviewer | ADR (`04`) implemented as documented; deps listed; extension seams (`09`) match reality | 🔴 | — | Code review sign-off each milestone |
| **Accessibility** | a11y reviewer | Keyboard journey passes; focus semantics; AA contrast; non-color states; axe scan (where runnable) | 🔴 | — | Screenshot/keyboard evidence + axe results |
| **Responsive** | designer + qa-tester | 1280 + 820 usable; charts/tables have documented alternatives at small widths | 🔴 | — | Screenshot evidence at both widths |
| **Reliability** | qa-tester | Loading/empty/validation/error/permission/not-found/service-down states handled on P0 screens | 🔴 | — | Failure-mode checklist (07) executed |
| **Clinical safety** | security/clin-safety reviewer | Assistant banner + citations + missing-info; honest no-result wording; no misleading affordances | 🔴 | — | Copy review + answer-content check |
| **Demo** | demo lead | 5–10 min script runs from cold stack; no dead ends; fallbacks work | 🔴 | — | Executed demo recorded (+ screenshots) |

## Scoring rule

`evidence per row + owner sign-off` = pass. A gate failing flips to ⛔ with a tracked blocker; fix and re-run the evidence step. Final release gate = all rows 🟢.

## Companion evidence file

`docs/ui-redesign/verification.md` (created during M6) records, per gate: commands run, outputs/SHA of key files, screenshots/Walkthrough artifacts, and known limitations.