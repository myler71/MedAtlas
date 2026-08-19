# 03 — Design System

## Visual direction

Calm, precise, modern, trustworthy. Information-dense without crowding. A focused clinical workstation, not a consumer wellness app. **Neutral-first** with a restrained accent and semantic status colors. Designed for long desktop sessions, functional on tablets. Consistent across charts, tables, forms, drawers, alerts, and evidence cards. **Light theme baseline; dark mode optional (non-blocking).**

Avoid: excessive gradients, glassmorphism, huge rounded cards, decorative charts, low-contrast gray-on-gray.

## Design tokens

Structure follows the existing `css/variables.css` (extend it; keep the current blue/slate neutral base).

- **Color:** neutral scale + one accent; semantic status tokens — `info`, `success`, `warning`, `danger` — each with a **paired text label/icon rule** so states are never color-only. Contrast targets WCAG 2.2 AA (4.5:1 text, 3:1 UI/graphics).
- **Typography:** system font stack (current), fixed type scale (display/title/body/caption/data), numeric styles (`font-variant-numeric: tabular-nums`) for tables and readings.
- **Spacing/radius/border/elevation:** 4px spacing scale, 4/6/8px radii, 1px borders, low-elevation shadows for drawers/toasts.
- **Motion:** ≤200ms, `prefers-reduced-motion` honored.
- **Focus:** global visible focus ring token (`:focus-visible`) on every interactive element.
- **Layout:** shell grid — top nav bar + content; patient context bar; document tested widths **1280 + 820 (P0 floor), 390 (P1)**; sub-390px is a non-goal.

## Component inventory (frozen for MVP)

`button` (primary/secondary/danger/ghost, sm/md/lg, loading `aria-busy`) · `card` + section header · `banner` (info/warning/error/success — icon+text) · `table` (sticky head, zebra; card-stack <720px) · `tabs` (ARIA tablist, arrow-key roving) · `drawer` (role=dialog, focus trap, Esc, backdrop, focus restore) · `skeleton loader` · `empty state` · `error state` (+ retry) · `toast` (`aria-live=polite`) · `state legend` (shape+label, never color-only) · `chips` · `form controls` (label/error/hint wiring).

**Any new abstraction requires an ADR note** — the inventory is intentionally frozen to bound Vanilla-JS scope.

## Chart-legend rules

- Every tooth/region state appears with **shape/pattern + text label**, not color alone.
- Accessible names carry state text: e.g. `aria-label="Tooth 16 (FDI), upper left, state: caries"`.
- A **text list alternative** accompanies each chart (dental: quadrants → teeth → state; skeleton: regions → bones → state) — doubles as the screen-reader view and the small-screen view.
- Skeleton orientation (left/right) is explicit in labels; schematic paths are labeled as schematic.

## Standard states

default · hover · focus · selected · active · disabled · loading · error · warning · success — defined per component in components.css, always with visible focus and never color-only.