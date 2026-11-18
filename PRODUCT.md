# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Design preview: one self-contained static HTML file (`frontend/design/index.html`). The production frontend is expected to be Next.js (TypeScript) talking to the existing FastAPI backend; this stack is not yet built.

## Users

Homeowners and commercial/corporate building owners or facility managers in Lahore, Pakistan, who have rooftop solar plus a battery. Single user per site. They look at it on a phone for short glances and on a laptop at a desk in roughly equal measure. Not factories or manufacturing units. English only.

## Product Purpose

SolarSense is an energy management layer on top of an existing inverter and battery (GoodWe today). It plans the battery around time-of-use tariffs and load-shedding, tells the user when washing the panels pays off, and reports savings in rupees. Success is the user understanding in seconds what the system is doing, what it will do next, and what it saved them.

## Positioning

It optimises for Pakistani grid reality: evening peak tariffs, frequent feeder outages with an outage-risk-aware backup reserve, dust-driven panel losses, and net-metering export credit that pays less than the retail rate. A generic global monitoring app does not model these.

## Operating Context

Lahore (Asia/Karachi, UTC+05:00). LESCO time-of-use tariffs with an evening peak around 18:00–22:00, off-peak the rest of the day, a net-metering export credit, and unscheduled outages. Panels soil with dust and smog. The system currently advises; automatic inverter control is not built.

## Capabilities and Constraints

- Built in the backend: 24-hour battery dispatch optimiser, solar and load forecasts, outage-risk classifier, panel-defect image classifier, soiling and cleaning economics.
- Not built: inverter control, user accounts, live telemetry, billing, assistant chat. The frontend has no billing or assistant screens; the rest show "coming soon" where relevant.
- Figures in the frontend are replays of recorded Station LHR-RES-01 data, not live, and must be labelled "Sample data".
- Auth is email and password only. Home and Building users see the same UI.
- Solid primary colour on a white background with a four-colour theme switcher (blue, amber, emerald, teal) is a binding requirement from the user.
- Factory concepts (MDI demand penalties, diesel backup) are out of scope.

## Brand Commitments

Name: SolarSense. No existing logo, brand colours or photography; the wordmark and mark are to be designed. The user wants the UI to look professional and distinctive, and explicitly not generic or AI-generated.

## Evidence on Hand

Real telemetry and tariff constants exist in the repo for a 7.02 kWp / 5.12 kWh Lahore residential station (see AGENTS.md). The frontend mocks use them (`frontend/src/services/mock/lhr-res-01.ts`); `frontend/design/index.html` still holds the original illustrative numbers. No customers, testimonials, pricing, benchmarks or photos exist; none may be invented.

## Product Principles

- Answer the user's question first: what is happening, what happens next, what did it save.
- Money and hours, not engineering jargon.
- Honest about what is advisory versus automatic and what is sample data.
- Built for Pakistani power conditions, not a global template.

## Accessibility & Inclusion

WCAG AA contrast for all four theme colours; full keyboard operation; respects reduced motion.
