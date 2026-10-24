# Historical decision methodology

## Scope and decision model
January 1–31 2026 decision dates purchase for the following Europe/London calendar day, including February 1. The configurable default 10:00 cutoff is illustrative, not a verified auction deadline. Calendar boundaries use Python zoneinfo; storage uses UTC-aware timestamps. Selection independently takes the latest publication <= cutoff for each target. Forecast age is cutoff minus publication; lead time is target minus publication. Missing forecasts remain missing. A conflicting latest vintage is quarantined rather than replaced by an older vintage.

## Verified data findings
Official documentation entrypoints:
- https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream
- https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream
- Official data dictionary (generation MW; historical WINDFOR description): https://www.elexon.co.uk/bsc/documents/groups/isg/2022-meetings-isg/253-may/isg253-04b-cp1562-neta-idd-part-1-redline-text-v49/

Direct API probes during implementation verified:
- Base URL: `https://data.elexon.co.uk/bmrs/api/v1`.
- `/datasets/WINDFOR/stream?publishDateTimeFrom=2026-01-01T00:00:00Z&publishDateTimeTo=2026-01-01T06:00:00Z` returned a JSON array of 146 records, two distinct publication times, and 73 distinct hourly targets. Fields: dataset, publishTime, startTime, generation. Historical vintages for the same target are available.
- Targets include December 31, despite the January 1 publication window: filters apply to publication time, not delivery time.
- `/datasets/FUELHH/stream?publishDateTimeFrom=2026-02-01T00:00:00Z&publishDateTimeTo=2026-02-02T00:00:00Z` returned 49 WIND records at 30-minute target spacing. February 1 23:30 is published February 2 00:00. This demonstrates the need to fetch beyond the last delivery date and deduplicate inclusive request boundaries.
- Responses use explicit UTC `Z` timestamps. No revision/version field appeared in these samples. Actuals include publishTime, settlementDate, settlementPeriod and fuelType.
- The official dictionary labels generation MW. Its older forecast description does not settle the precise interval semantics of the hourly January 2026 feed.

The documentation pages were JavaScript-only through the browser fetch tool; a guessed `/swagger.json` returned 404. Small direct data requests succeeded after network access approval. Maximum allowed query spans, pagination/truncation guarantees, and current forecast interval semantics remain unresolved. The implementation uses one-day bounded stream requests without inventing pagination parameters. This is a documented verification limitation, not proof of exhaustive source coverage.

## Alignment and metrics
Use an expected hourly grid built from local delivery boundaries: 24 targets/day in this January scope, 744 across the period. Compare only exact timestamps; do not expand forecasts, aggregate actuals, interpolate or forward-fill. This evaluates the hourly subset of half-hour outturns; it is not whole-day energy accuracy. Report expected, eligible forecast, available actual, matched, missing and conflicting counts separately. Coverage denominator is the expected hourly grid, not the number of returned records. Source-wide invalid/conflict counts are in the manifest.

Signed error = forecast MW minus actual MW: positive is overforecast. MAE, RMSE and bias use matched valid observations with equal target spacing. Period metrics use all underlying observations. Empty matches produce null metrics and explanatory status. No MAPE, energy totals, procurement quantities, costs or savings are claimed.

## Snapshot and quality policy
Ingestion requests forecast publications December 25–January 31 and actual publications January 1–February 3, filtering normalized targets to January 2–February 1. A week of forecast warm-up is a bounded assumption; any target without an eligible publication remains missing. Actuals are retrieved historical outturn within this extraction window, not information known at the purchasing cutoff and not guaranteed final revisions.

Only WIND actuals are retained. Null/nonfinite/nonnumeric values and timezone-naive/malformed timestamps are rejected; zero is valid. Identical key/value duplicates collapse. Forecast key is target + publication; actual key is target. Without a verified revision ordering, differing values for a key become a conflict with null generation; no arbitrary winner is selected. Raw JSON retains rejected records for audit; the manifest reports counts. Adjacent inclusive windows can create harmless exact duplicates.

Each request records URL, parameters, retrieval timestamp, row count and checksum. Normalized content is SHA-256 addressed, and an atomic manifest replacement activates it only after successful ingestion. Failed ingestion leaves an existing snapshot intact. Restart the API after ingestion to load the new immutable snapshot. No synthetic data is substituted. Application request handlers never fetch Elexon.

## Full snapshot observations
The completed extraction contains 17,864 normalized forecast target/publication pairs and 1,488 WIND actuals across the 31 delivery days. It found zero invalid records and zero conflicting keys; 33 actual duplicate rows were collapsed at request boundaries. At the default cutoff all 744 expected hourly evaluation targets matched. This establishes coverage of the chosen grid, not the completeness of every possible source vintage. The recorded snapshot ID is `fe68b1de29f057fc012fa031ab4fc8967484f79cb7e0ff7135048acab17808a5`. See `docs/snapshot-summary.json` for the actual run's daily coverage and period metrics. Raw requests and provenance are preserved under `data/` and eligible for version control.


## Backend review: alignment detail and reproducibility
The hourly grid includes `00:00`, `01:00`, … `23:00` on each local delivery day. FUELHH records beginning at `:00` are included when valid; records beginning at `:30` are excluded. The selected actual is the MW outturn for that particular half-hour settlement period `[t, t+30 minutes)`, not an hourly average. No two half-hours are combined. Matching timestamps alone does not establish identical measurement intervals; the forecast's point/interval semantics remain unresolved. The official [NETA dictionary, FUELHH section](https://bscdocs.elexon.co.uk/bsc-module/interface-definition-documents/neta-interface-definition-and-design-document-part-1-interfaces-with-bsc-parties-and-their-agents/v-57-0/id-67b34bd747c7f13fbb2970f5) describes generation for a particular half hour, in MW.

The chosen evaluation grid has 24 targets per January decision day and 744 for the complete scope. Matched coverage is matched valid target pairs divided by expected grid targets, so 100% means complete coverage of this hourly subset, not all 1,488 half-hour actual records. Missing counts include quarantined conflicts, which are also reported separately. Metadata exposes the 60-minute evaluation spacing, 30-minute actual interval, denominator, alignment policy and limitation.

Raw-record checks independently filtered the preserved WINDFOR responses by target and cutoff and found the maximum eligible publication. Examples, including an exactly-at-cutoff publication, are saved in `selection-examples.json`. Re-run from `backend` using `../.venv/bin/python -m scripts.verify_raw_selection`. All 72 raw response checksums and the normalized snapshot checksum were verified. No Elexon network access is involved in startup, evaluation or these checks. Source URLs, query parameters, per-request timestamps, checksums, row counts and retrieval time are in the manifest. Raw data is excluded only from the Docker image, not version control.

## Product validation audit
Both supplied Elexon pages were successfully read in a JavaScript-enabled Chromium browser on 24 October 2026. FUELHH explicitly describes 30-minute average MW values for Great Britain; WINDFOR documents publication-time filtering and the latest-only default when those filters are omitted. Its exact forecast measurement interval remains unspecified in the inspected page. Fresh bounded API probes succeeded. All 744 default-cutoff selections were independently checked against preserved raw responses, with matching actual values. See [requirements-audit.md](requirements-audit.md), [live-source-probes.json](live-source-probes.json) and [snapshot-audit.json](snapshot-audit.json). The existing exact-match policy is retained; none of these checks establishes identical forecast/actual measurement intervals.
