# SolarSense frontend

Next.js (App Router, TypeScript strict) web app for SolarSense: a home or building owner sees what their
solar and battery are doing, what they will do next, and what they saved. It is a pixel-exact port of the
design preview in [`design/index.html`](design/index.html), which stays in the repo as the visual reference.

All screens run on **recorded data from Station LHR-RES-01** (the 7.02 kWp / 5.12 kWh Lahore home system in the
Python backend's datasets) behind a typed service layer; nothing talks to the FastAPI backend yet (see
[Wiring a real endpoint](#wiring-a-real-endpoint)). The values are copied from the backend's CSVs and tariff
file into `src/services/mock/lhr-res-01.ts` and `lhr-res-01-history.ts`; each block names its source file.

## Requirements

- Node 24 or newer (`.nvmrc`)
- pnpm 12 (pinned in `packageManager`)

## Commands

Run everything from this folder (`frontend/`), not from the repo root.

| Command                             | What it does                                                                              |
| ----------------------------------- | ----------------------------------------------------------------------------------------- |
| `pnpm install`                      | Install dependencies                                                                      |
| `pnpm dev`                          | Dev server on http://localhost:3000                                                       |
| `pnpm build` then `pnpm start`      | Production build and server                                                               |
| `pnpm typecheck`                    | `tsc --noEmit`                                                                            |
| `pnpm lint`                         | ESLint (Next, TypeScript, jsx-a11y rules)                                                 |
| `pnpm format` / `pnpm format:check` | Prettier (with the Tailwind class sorter)                                                 |
| `pnpm test`                         | Vitest unit and component tests                                                           |
| `pnpm test:e2e`                     | Playwright: smoke, accessibility (axe), responsive and motion checks. Needs a build first |
| `pnpm parity`                       | Pixel comparison against `design/index.html`. Needs a build first                         |

First time with Playwright: `pnpm exec playwright install chromium`.

## Structure

```
src/
  app/                 Routes only. Route groups: (marketing) /, (auth), (onboarding), (app)
  features/<screen>/   Screen composition, view-models (pure) and feature-only components
  components/
    ui/                Design-system primitives, no solar or backend knowledge
    forms/             Field, validation wiring, error summary
    charts/            Hand-built SVG charts (plan, bar, line, energy flow)
    layout/            App shell, sidebar, top bar, public shell
    brand/             Logo
    illustrations/     Flat SVG illustrations
  providers/           Toast, alerts, sample clock
  hooks/               Reusable hooks (focus trap, count-up, scroll spy, chart sizing)
  lib/                 Pure helpers: formatting, validators, chart maths, storage
  services/            Repositories (mock today), mock engine, getServices()
  types/domain/        UI-language domain types
  config/              Navigation table
  styles/              Tokens, theme and the design's CSS, ported verbatim
e2e/                   Playwright specs and the parity harness (e2e/parity)
scripts/               Small dev helpers used while checking parity
design/                The reference design (do not edit)
```

Dependency direction: `app` -> `features` -> `components` -> `lib` / `hooks` / `types`. `services` is only
reached from `app` and `features`. `components/ui` must not import from `features`, `services` or
`types/domain` (ESLint enforces this).

## Data and the service layer

Screens call `getServices()` (`src/services/index.ts`) on the server and receive typed domain objects.
Every repository is a small interface plus a deterministic mock:

```
src/services/repositories/<name>/<name>.repository.ts   interface
src/services/repositories/<name>/<name>.mock.ts         sample data
```

The mock engine (`src/services/mock/engine`) is a pure, deterministic replay of one recorded day (26 Oct 2026):
solar and usage come from the inverter telemetry, and the engine adds the battery level and grid import. The
battery rules it follows (15% reserve floor, charge and discharge limits, discharge only in the evening peak)
are unit-tested. Figures are replays of recorded data, not live, and carry a "Sample data" label. Other screens
use the metered monthly balance, outage log, inverter alarms and the backend's soiling model; where the data
ends (hourly data on 7 Oct 2026, telemetry on 27 Oct 2026) the screen says so.

### Wiring a real endpoint

The backend (`src/api` in the repo root) exposes `/health`, `/api/window`, `/api/optimize` and
`/api/backtest/stream`. Forecast, outage-risk, soiling and vision have no HTTP routes yet. To switch one
screen to real data:

1. Add `<name>.http.ts` next to the repository interface, implementing the same interface.
2. Validate the response at the edge (add a schema for the Pydantic model) and map it to the domain type in
   `types/domain`. The backend is factory-scale (`factory_load_kw`, MDI, diesel); the UI speaks home-scale,
   so the mapper is where those fields are renamed or dropped.
3. Return the http implementation from `getServices()`.

`.env.example` lists `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_USE_MOCKS`. Copy it to `.env.local` when you
need them (never commit `.env` files).

State is kept simple on purpose: React context for toasts, alerts and the sample clock; local state
elsewhere. TanStack Query is not used yet; add it when the first client-driven fetch exists (for example a
what-if `POST /api/optimize` or the backtest stream).

## Themes

A single blue theme (`navy`) sets `--primary`, `--hover`, `--accent` and the sidebar overlays on
`<html data-theme="navy">`. There is no colour switcher. Tokens live in `src/styles/tokens.css`; `theme.css` maps
them into Tailwind v4 so utilities follow the theme.

The design's component CSS is ported verbatim into `src/styles/components/` (unlayered, so it wins over
Tailwind utilities). Tailwind's preflight is deliberately not imported: the design's own base rules are the
only reset, which keeps rendering identical to the design.

## Accessibility and motion

- Semantic landmarks, a skip link, labelled icon buttons, focus-visible rings and 44px touch targets below 1024px.
- Keyboard: tabs (arrows, Home, End), the chart hour slider (arrows, Home, End), drawers and dialogs (focus is
  trapped and returned).
- `prefers-reduced-motion` removes entrance animations, stagger delays, and count-ups.
- Looping decorations (dashed flow lines, rays, pulses) are paused while off screen
  (`src/lib/offscreen-loops.ts`, mounted by `OffscreenLoops`). Animations on SVG shapes cannot run on the
  compositor, so each one would otherwise cost main-thread time on every frame; on the landing page that
  was about 0.9 s of CPU per 3 s while idle.
- Every chart has a "View as table" alternative.
- `pnpm test:e2e` runs axe on every screen and fails on serious or critical violations.

## Design parity

`pnpm parity` opens each screen in `design/index.html` and in the built app (Chromium, motion frozen, same font
file) and compares full-page screenshots pixel by pixel with zero tolerance. Failures are written to
`parity-report/` (git-ignored) as `<route>-<theme>-<width>.{a,b,diff}.png`.

Run `pnpm build` first (the harness starts `pnpm start -p 3100`).

| Variable                        | Meaning                                                              |
| ------------------------------- | -------------------------------------------------------------------- |
| `PARITY_FULL=1`                 | All widths (default: 375 and 1280)                                   |
| `PARITY_ROUTES=login,dashboard` | Limit to these routes                                                |
| `PARITY_WIDTHS=375,1024`        | Limit to these widths                                                |
| `PARITY_SELF=1`                 | Compare the design with itself (proves the harness is deterministic) |
| `PARITY_TOLERANCE=0.0005`       | Allowed share of differing pixels (default 0)                        |

Helpers in `scripts/`: `diff-summary.mjs` (where a diff is), `crop.mjs` (zoom into a region of a pair),
`rect-check.mjs` (compare element boxes in design and app), `overflow-check.mjs` (what overflows the viewport),
`font-check.mjs` (which font files each page loads).

### Deliberate differences from the preview

- The design's "Preview:" screen switcher is not ported (hidden in both pages while comparing).
- "(preview)" is removed from product copy, and not-yet-built actions say they are coming soon instead
  (`e2e/parity/intentional-diffs.ts` applies the one visible case to the design before comparing).
- Inter is served from `src/app/fonts/inter-latin-variable.woff2`; the harness serves the same file to the design.
- Fixes to defects found in the preview: the live clock no longer redraws the chart (so keyboard focus on the
  hour slider survives), reduced motion also zeroes animation delays,
  and the alert count in the sidebar and bell follows "Mark all as read".

## Adding a screen

1. Add the repository (interface and mock) if it needs data, and register it in `getServices()`.
2. Put pure logic in `features/<screen>/view-model.ts` with a test next to it.
3. Add `src/app/(app)/<screen>/page.tsx` (thin: fetch, then render the feature) and the nav entry in `config/nav.ts`.
4. Add the route to `e2e/routes.ts` and `e2e/parity/config.ts`, then run `pnpm parity`.
