# Wind Desk frontend

Implemented React 19 + TypeScript + Vite with Recharts and Lucide icons. Forest/ivory/mint visual design; responsive desktop and mobile layouts.

## Features
- Overview: daily MAE, RMSE, signed bias, coverage, forecast/actual chart, clickable monthly MAE bars, completeness grid and target observations.
- Decision explorer: only the decision endpoint's selected forecasts, publications, age and lead time; no actual outcomes in the view or CSV.
- Accuracy trends: full-January underlying-observation metrics, daily MAE and signed bias charts, daily metric table.
- Forecast vintages: selectable delivery targets, publication history, selected/earlier-eligible/after-cutoff labels, lead times and timeline chart. Changing decision date updates the delivery target to the following day.
- Data/methodology: source row counts, retrieval time, checksum, quality counts, alignment, metric definitions and explicit limitations.
- Date stepping, strict cutoff input with Apply, CSV export, mobile navigation, loading states and unavailable-backend/snapshot errors with Retry.

All analysis comes from the existing API; there is no demo-data fallback or client recomputation of period metrics. Actuals are labelled as half-hour values. The original measurement-interval limitations remain visible.

## Verification actually run
- TypeScript and Vite production build passed.
- Real-API Chromium smoke pass: all five screens, January 31 to February 1 boundary, no actual columns/series in the decision view, applied 04:30 cutoff, CSV download, mobile navigation, no horizontal page overflow at 390px, simulated 503 and successful retry. No page errors.
- Desktop (1440px) and mobile (390px) screenshots captured and visually inspected.
- Frontend Docker image built successfully with npm ci, TypeScript/Vite and Nginx. Full-stack Compose startup succeeded on port 5174. The same browser smoke suite passed against the production Nginx service, including real API requests, Swagger documentation proxy, all five views and error recovery.
- Verification covers local builds and containers; it does not claim a hosted deployment.

## Commands
Backend: `BACKEND_PORT=8001 docker compose up -d --wait backend` from root.
Frontend: `cd frontend && npm ci && npm run dev`, then http://localhost:5173.
Production build: `npm --prefix frontend run build`.
Browser smoke: `npm --prefix frontend run test:smoke` with Chromium installed (first run: `cd frontend && npx playwright install chromium`).
Full Docker app: `BACKEND_PORT=8001 FRONTEND_PORT=5174 docker compose --profile dashboard up -d --build`, then http://localhost:5174. Port 5174 can coexist with Vite at 5173. Nginx proxies /api, /docs and /openapi.json to the backend service.

## Verification limits
Hosted end-to-end verification remains to be performed after deployment. Fonts are loaded from Google Fonts with system fallback if unavailable. Broader browser/accessibility testing has not been performed.

Visual references: [desktop](screenshots/dashboard-desktop.png) and [mobile](screenshots/dashboard-mobile.png).


## Interaction and visual refinement
- All eight daily/period metric cards are keyboard-accessible buttons opening native dialogs with formulas, matched/expected counts and largest absolute misses or missing-data breakdowns. Dialogs trap focus, restore it on close, and support Escape.
- Overview explicitly labels historical evaluation and actual outcomes. Decision explorer defaults to decision-only API data; an explicit “Show historical actuals” switch requests evaluation data. Turning it off removes actuals from chart, tooltip, table and CSV. Request state is keyed by endpoint so a previous evaluation response cannot flash in the decision view.
- Full decision cutoff date, GMT and Europe/London are visible. On Accuracy, the caption correctly states the cutoff applies separately to every January decision date.
- Alignment explanation is available beside metrics and inside every metric dialog, with the 12:00–12:30 actual example and unresolved interval-semantics limitation.
- Forecast tooltips show target date/time, forecast, half-hour actual, signed error and selected publication time. Decision-only tooltips exclude outcomes.
- Coverage blocks link to target publications; MAE and bias charts open the selected daily evaluation. The static GB workspace no longer suggests an unavailable dropdown.
- Exports match their view: 24-target daily CSV, 744-target period CSV, or target publication-history CSV. Decision-only CSV excludes actual columns.
- Palette refreshed to navy, teal, lavender and copper; supporting text/axes are darker and actual series has a stronger copper dash.

Validation: `npm run build` passed; `node scripts/interactions.mjs` passed against the real backend through the development proxy. This checked all eight metric cards, keyboard dialogs, alignment explanation, tooltip fields, date arrows, table expansion, coverage links, target selector, CSV contents/counts, explicit actual toggle, cutoff application, both daily charts, daily table links, January 31 delivery boundary, help, source link destinations and mobile overflow. External Elexon destinations were inspected as links rather than browser-tested. Existing smoke checks continue to verify unavailable-snapshot retry. Desktop/mobile/modal screenshots were captured and inspected.

Final production verification: the expanded interaction audit also passed against the rebuilt Docker dashboard at `http://localhost:5174`, with no page errors. The development preview was stopped; Docker services remain running.
