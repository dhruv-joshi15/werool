# Product validation report

Wind Desk provides historical decision-time forecast exploration and quantitative error analysis for national Great Britain wind generation. The January 2026 snapshot is reproducible and works locally through Docker or Python/Vite.

## Functional coverage

| Capability | Validation |
| --- | --- |
| Elexon-only application data | Source manifest contains FUELHH and WINDFOR; actuals filtered to WIND |
| Historical forecast selection | All 744 default-cutoff selections independently matched preserved raw responses |
| Calendar scope | January 1–31 decisions map to January 2–February 1 deliveries |
| Accuracy analysis | Daily/period MAE, RMSE, signed bias and expected-grid coverage |
| Decision/outcome separation | Actual outcomes hidden unless explicitly enabled; decision CSV excludes actual columns |
| Product interactions | Metric dialogs, chart navigation, dates, cutoffs, vintages, exports, error recovery and mobile layout checked |
| Local runtime | Python API and production React dashboard served successfully through Docker |

## Source verification

The [FUELHH documentation](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream) and [WINDFOR documentation](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream) were read in a JavaScript-enabled browser. FUELHH specifies average MW over 30-minute periods. WINDFOR supports publication filters and returns the latest publication if filters are omitted. Ingestion always supplies publication windows.

Fresh source probes returned HTTP 200: WINDFOR January 15 00:00–12:00 UTC returned 292 rows with four publications and hourly targets; FUELHH February 1–2 returned 980 source rows including 49 WIND rows at 30-minute target spacing. Evidence: [live probes](live-source-probes.json).

## Recorded checks

- 15 offline backend tests passed; one upstream Starlette/httpx deprecation warning.
- 744 default-cutoff selections and paired actual values independently verified against raw data; 72 raw response checksums checked.
- TypeScript/Vite production build passed.
- All six running API endpoints returned 200; an invalid scope returned 422.
- Browser smoke and interaction checks passed against the Docker dashboard, including simulated 503/retry, all eight metric cards, keyboard dialogs, CSV contents, both daily charts and mobile overflow.
- Backend was healthy on port 8001; frontend served the production build on port 5174.

See [snapshot audit](snapshot-audit.json), [backend verification](implementation-status.md) and [frontend verification](frontend-status.md).

Default-cutoff period metrics: 744/744 hourly pairs, MAE 1995.5685483870968 MW, RMSE 2498.8245110107187 MW, bias +1727.9825268817203 MW. These are snapshot-specific hourly-subset comparisons.

## Limits

Forecast target spacing is hourly; actual values describe half-hour averages. Matching timestamps does not establish equal measurement intervals. The exact-match hourly subset is explicit and does not imply full half-hour or energy accuracy. Forecast interval semantics, maximum source ranges and truncation guarantees remain unresolved.

The 10:00 cutoff is illustrative, not a verified auction deadline. Historical actuals are retrieved outturns within a bounded extraction window, not decision-time information or guaranteed final revisions. A bounded publication warm-up is used. No additional procurement, cost, demand or savings calculation is supported.

Public-hosted verification is separate from local checks. The Vercel configuration is prepared but has not been exercised in a hosted deployment.
