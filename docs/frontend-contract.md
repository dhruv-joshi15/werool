# Frontend API contract

Verified against the running Docker backend at `http://localhost:8001`. Interactive schemas: `/docs`; machine-readable contract: `/openapi.json`. CORS defaults to `http://localhost:5173`; set comma-separated exact origins with `CORS_ORIGINS` before starting the service. Only GET endpoints are needed.

## Endpoints and inputs

| Endpoint | Query parameters | Response |
| --- | --- | --- |
| `/api/v1/health` | none | service, dataset_ready, snapshot_id; service may be healthy with dataset_ready false |
| `/api/v1/metadata` | none | supported decision dates, timezone, cutoff, evaluation and actual resolution, alignment limitation, assumptions, source manifest |
| `/api/v1/decision` | required `date=YYYY-MM-DD`; optional `cutoff=HH:MM` | decision/delivery context, coverage, hourly observations with selected forecasts; actual outcome fields omitted |
| `/api/v1/evaluation` | same as decision | historical forecast/actual pairs, errors and daily metrics |
| `/api/v1/accuracy` | required `from`, `to` inclusive decision dates; optional cutoff | metrics across underlying matched observations and daily evaluation breakdown |
| `/api/v1/forecast-vintages` | required `start_time`, ISO timestamp with timezone | saved publication history for one exact target, including conflicts |

Decision dates are January 1–31, 2026 inclusive; deliveries are January 2–February 1. Timezone: Europe/London. January is UTC+00:00, but the implementation uses timezone-aware local calendar boundaries rather than fixed offsets. Default 10:00 is illustrative, not a verified auction deadline. Cutoff must be zero-padded 24-hour HH:MM. Encode `+` offsets as `%2B` in query strings, or use UTC `Z`.

## Meaning of values
All generation and error values are **MW**. `signed_error_mw = forecast_mw - actual_mw`: positive means overforecast, negative means underforecast. `absolute_error_mw` is its magnitude. MAE, RMSE and bias use valid matched observations; period metrics do not average daily metrics. No energy, trading cost or procurement result is provided.

Each observation has `start_time`, `forecast_mw`, selected `publish_time`, `forecast_conflict`, `forecast_age_hours` (decision cutoff minus publication), and `lead_time_hours` (target minus publication). Age and lead time are null if no vintage exists. A conflicting latest eligible vintage retains its publication and conflict flag but has null generation. Selection is independent per target, includes publications exactly at cutoff, and excludes later publications.

Evaluation adds `actual_mw`, `actual_conflict`, `signed_error_mw`, `absolute_error_mw`. Actuals are retrieved historical outturns; they are not claimed to have been available at decision time. Do not use evaluation outcomes in a decision-only view.

## Alignment and coverage
`evaluation_resolution_minutes=60` is target-grid spacing. `actual_interval_minutes=30` in metadata describes FUELHH's half-hour periods. Policy: `exact_timestamp_hourly_subset_no_interpolation`. At each `:00` target use only the actual half-hour record beginning then; exclude all `:30` records. That actual describes `[t,t+30 minutes)`, **not a full-hour average**. No interpolation or aggregation occurs. Matching timestamps alone does not establish identical measurement intervals; forecast interval semantics remain unverified. Label charts as an hourly target subset of half-hour outturns, not whole-day energy accuracy.

Coverage fields are counts over the expected grid:
- `expected_intervals`: 24 per January decision date, 744 over all 31 dates.
- `eligible_forecast_intervals`: targets with selected, valid, nonconflicting forecasts.
- `available_actual_intervals`: targets with valid, nonconflicting actuals (evaluation only).
- `matched_intervals`: targets having both valid values (evaluation only).
- `missing_forecasts`, `missing_actuals`: expected targets without a valid value, including conflicts.
- `forecast_conflicts`, `actual_conflicts`: conflicting target counts, also included in missing counts.

Metrics use `matched_count`, `expected_count`, and `coverage_percent = 100 * matched_count / expected_count`. 100% covers only the selected hourly grid. Source-wide invalid/duplicate/conflict counts are separately available in `metadata.snapshot.quality`.

## Missing values and errors
Missing values use JSON null; zero MW is valid. Do not convert null to zero. A valid query with zero matched pairs returns 200, status `no_matched_observations`, zero matched count and null MAE/RMSE/bias. Its coverage is 0% when the expected grid is nonempty. Empty vintage history returns an empty list. A selected forecast can exist without an actual and vice versa.

Invalid date, reversed/out-of-scope range, missing required parameter, malformed cutoff or timezone-naive vintage timestamp returns 422 with `detail` (string for domain checks, list for FastAPI validation). Missing/invalid snapshot returns 503 with `{"detail":"Historical snapshot unavailable or invalid; run ingestion and restart the backend"}`. Health remains 200 with dataset_ready false. Display unavailable dataset separately from a valid query with missing observations.

## Actual response examples
The following are excerpts generated from the container's real responses, with long arrays deliberately reduced to their first item. Complete captured responses are in [api-examples.json](api-examples.json); these are real snapshot examples, not fixtures.

### health

`GET /api/v1/health` → 200

```json
{
  "service": "ok",
  "dataset_ready": true,
  "snapshot_id": "fe68b1de29f057fc012fa031ab4fc8967484f79cb7e0ff7135048acab17808a5"
}
```

### metadata

`GET /api/v1/metadata` → 200

```json
{
  "actual_interval_minutes": 30,
  "alignment_limitation": "Timestamp equality does not establish identical measurement intervals: each actual is the half-hour settlement-period MW value starting at that timestamp, not a full-hour average. Forecast interval semantics remain unverified.",
  "coverage_denominator": "Expected hourly targets within the requested local delivery days (24 per January decision date; 744 for all 31 dates)",
  "supported_decision_dates": {
    "from": "2026-01-01",
    "to": "2026-01-31"
  },
  "timezone": "Europe/London",
  "default_cutoff": "10:00",
  "evaluation_resolution_minutes": 60,
  "alignment_policy": "exact_timestamp_hourly_subset_no_interpolation",
  "assumptions": [
    "10:00 is illustrative, not a verified auction deadline",
    "Hourly exact matches compare forecast targets with half-hour outturn starting at the same timestamp; this is not whole-day energy accuracy",
    "Actuals are retrieved historical values; conflicts are quarantined",
    "Forecast interval semantics and API maximum range remain unresolved"
  ],
  "snapshot": {
    "snapshot_id": "fe68b1de29f057fc012fa031ab4fc8967484f79cb7e0ff7135048acab17808a5",
    "retrieved_at": "2026-10-24T14:07:16.491315Z",
    "quality": {
      "forecasts": {
        "invalid": 0,
        "duplicates": 0,
        "conflicts": 0,
        "filtered": 0
      },
      "actuals": {
        "invalid": 0,
        "duplicates": 33,
        "conflicts": 0,
        "filtered": 31654
      }
    },
    "row_counts": {
      "forecasts": 17864,
      "actuals": 1488
    },
    "coverage": {
      "forecasts": {
        "first_target": "2026-01-02T00:00:00Z",
        "last_target": "2026-02-01T23:00:00Z"
      },
      "actuals": {
        "first_target": "2026-01-02T00:00:00Z",
        "last_target": "2026-02-01T23:30:00Z"
      }
    },
    "limitations": [
      "One-week publication warm-up is bounded; absent eligible forecasts remain missing",
      "Actual publications retrieved through February 3; later revisions are not included",
      "One-day stream requests; API maximum range and truncation guarantees unverified"
    ]
  }
}
```

### decision

`GET /api/v1/decision?date=2026-01-15&cutoff=10:00` → 200

```json
{
  "decision_date": "2026-01-15",
  "decision_timestamp": "2026-01-15T10:00:00Z",
  "delivery_date": "2026-01-16",
  "cutoff": "10:00",
  "timezone": "Europe/London",
  "evaluation_resolution_minutes": 60,
  "alignment_policy": "exact_timestamp_hourly_subset_no_interpolation",
  "context": "as_of_decision_no_outcomes",
  "coverage": {
    "expected_intervals": 24,
    "eligible_forecast_intervals": 24,
    "missing_forecasts": 0,
    "forecast_conflicts": 0
  },
  "observations": [
    {
      "start_time": "2026-01-16T00:00:00Z",
      "forecast_mw": 7472.0,
      "publish_time": "2026-01-15T09:30:00Z",
      "forecast_conflict": false,
      "forecast_age_hours": 0.5,
      "lead_time_hours": 14.5
    }
  ],
  "metrics": null
}
```

### evaluation

`GET /api/v1/evaluation?date=2026-01-31&cutoff=10:00` → 200

```json
{
  "decision_date": "2026-01-31",
  "decision_timestamp": "2026-01-31T10:00:00Z",
  "delivery_date": "2026-02-01",
  "cutoff": "10:00",
  "timezone": "Europe/London",
  "evaluation_resolution_minutes": 60,
  "alignment_policy": "exact_timestamp_hourly_subset_no_interpolation",
  "context": "retrieved_historical_outturn_evaluation",
  "coverage": {
    "expected_intervals": 24,
    "eligible_forecast_intervals": 24,
    "missing_forecasts": 0,
    "forecast_conflicts": 0,
    "available_actual_intervals": 24,
    "missing_actuals": 0,
    "actual_conflicts": 0,
    "matched_intervals": 24
  },
  "observations": [
    {
      "start_time": "2026-02-01T00:00:00Z",
      "forecast_mw": 10474.0,
      "publish_time": "2026-01-31T09:30:00Z",
      "forecast_conflict": false,
      "forecast_age_hours": 0.5,
      "lead_time_hours": 14.5,
      "actual_mw": 8724.0,
      "actual_conflict": false,
      "signed_error_mw": 1750.0,
      "absolute_error_mw": 1750.0
    }
  ],
  "metrics": {
    "status": "ok",
    "mae_mw": 814.0833333333334,
    "rmse_mw": 921.1421804839179,
    "bias_mw": 803.8333333333334,
    "matched_count": 24,
    "expected_count": 24,
    "coverage_percent": 100.0,
    "positive_count": 23,
    "negative_count": 1,
    "zero_count": 0
  }
}
```

### accuracy

`GET /api/v1/accuracy?from=2026-01-01&to=2026-01-31&cutoff=10:00` → 200

```json
{
  "from_date": "2026-01-01",
  "to_date": "2026-01-31",
  "cutoff": "10:00",
  "metrics": {
    "status": "ok",
    "mae_mw": 1995.5685483870968,
    "rmse_mw": 2498.8245110107187,
    "bias_mw": 1727.9825268817203,
    "matched_count": 744,
    "expected_count": 744,
    "coverage_percent": 100.0,
    "positive_count": 627,
    "negative_count": 117,
    "zero_count": 0
  },
  "daily": [
    {
      "decision_date": "2026-01-01",
      "coverage": {
        "expected_intervals": 24,
        "eligible_forecast_intervals": 24,
        "missing_forecasts": 0,
        "forecast_conflicts": 0,
        "available_actual_intervals": 24,
        "missing_actuals": 0,
        "actual_conflicts": 0,
        "matched_intervals": 24
      },
      "metrics": {
        "status": "ok",
        "mae_mw": 3156.6666666666665,
        "rmse_mw": 3212.853715935414,
        "bias_mw": 3156.6666666666665,
        "matched_count": 24,
        "expected_count": 24,
        "coverage_percent": 100.0,
        "positive_count": 24,
        "negative_count": 0,
        "zero_count": 0
      }
    }
  ]
}
```

### forecast vintages

`GET /api/v1/forecast-vintages?start_time=2026-02-01T00:00:00Z` → 200

```json
{
  "start_time": "2026-02-01T00:00:00Z",
  "vintages": [
    {
      "start_time": "2026-02-01T00:00:00Z",
      "publish_time": "2026-01-30T02:30:00Z",
      "generation_mw": 11131.0,
      "conflict": false
    }
  ]
}
```

### invalid date

`GET /api/v1/decision?date=2026-02-01` → 422

```json
{
  "detail": "Decision date must be within January 2026"
}
```

## Remaining limitations
Forecast point/interval semantics, API maximum spans and truncation guarantees remain unverified. The extraction has a bounded publication warm-up and actual revision window; snapshot provenance records both. There are no invalid/conflicting source records in this snapshot, but the API supports those states. No live refresh occurs in request handlers. Rebuild/restart after an explicit snapshot refresh. The React interface is implemented; see `frontend-status.md`. Hosted deployment verification is separate.
