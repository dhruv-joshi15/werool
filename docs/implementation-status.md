# Backend review and verification

The backend and React dashboard implement historical wind forecast analysis. See [frontend-status.md](frontend-status.md) for interface verification.

## Material fixes
- The original ignore rules excluded the saved manifest and normalized snapshot. Those rules were removed. Raw records are also eligible for version control so the offline audit is reproducible; Docker continues to exclude raw records. A temporary Git index/ignore audit confirmed all 74 required snapshot/provenance files are eligible. Dependency installation was also verified in a clean Linux container; local verification did not include an independent fresh Git clone.
- Compose now serves the snapshot baked into the image without host bind mounts. Host port is configurable with `BACKEND_PORT`; readiness checks require dataset_ready true. Runtime user is non-root (verified UID 1000).
- Malformed non-string timestamps now raise a validation error instead of crashing normalization. Added a deterministic regression test.
- Metadata explicitly provides 30-minute actual intervals, 60-minute evaluation spacing, coverage denominator and the limitation that timestamp equality does not establish equal measurement intervals.
- Replaced an ineffective period-weighting assertion with an API regression using unequal matched counts across two days and future publications that must be excluded. Added missing-data/alignment, additional API validation and timezone checks.

## Checks actually performed
- **15 offline pytest tests passed**; final recorded run 0.51 seconds. One upstream Starlette/httpx TestClient deprecation warning; no test failures. Tests cover selection, coverage, metrics, boundaries, validation and missing-dataset behaviors.
- Independent selection audit against saved raw WINDFOR responses passed for four examples, including exact-cutoff inclusion. Results: [selection-examples.json](selection-examples.json). All 72 raw response SHA-256 checksums and the normalized content-addressed snapshot identity verified. Manifest retrieval: `2026-10-24T14:07:16.491315Z`.
- Docker daemon reachable, version 27.5.1. `docker compose build` succeeded, including dependency installation in a clean Python 3.12 Linux base. This verifies the lock file and code/data paths independently of the host venv.
- Final reviewed image started via `BACKEND_PORT=8001 docker compose up -d --wait`; container is healthy and left running. Startup logs showed application startup complete without errors. No unrelated services/resources were changed.
- Real HTTP checks against `http://localhost:8001`: health, metadata, decision, evaluation, accuracy and forecast-vintages all returned **200**. Invalid out-of-scope decision returned **422**. Full captured responses: [api-examples.json](api-examples.json).
- Final container smoke script confirmed decision observations omit actuals, January 31 maps to February 1, every selected period-evaluation publication is <= its decision cutoff, and period metrics match the original snapshot summary exactly.
- Snapshot accessible inside container: 17,864 forecast vintages and 1,488 actuals, ID `fe68b1de29f057fc012fa031ab4fc8967484f79cb7e0ff7135048acab17808a5`. No host data mount is configured. Startup/request handlers have no ingestion calls and require no Elexon access.
- Default evaluation: **744/744 hourly targets (100%)**; MAE **1995.5685483870968 MW**, RMSE **2498.8245110107187 MW**, bias **+1727.9825268817203 MW**. These are hourly-subset comparisons against half-hour actual values, not full-hour averages or whole-day energy accuracy.

## Remaining limits
Forecast point/interval semantics, maximum source query ranges and truncation guarantees remain unresolved. Publication warm-up and actual revision windows are bounded and documented. The source values are retrieved historical actuals, not decision-time information. Build dependency installation requires registry access, but normal API startup does not need Elexon network access. No secrets or machine-specific paths are required. Windows-native portability is not verified; the supported Docker path uses Linux. Frontend browser smoke checks passed; hosted deployment verification remains separate.

## Commands from project root

```sh
docker compose build
BACKEND_PORT=8001 docker compose up -d --wait
curl http://localhost:8001/api/v1/health
python3 backend/scripts/verify_api.py --base-url http://localhost:8001
```

Open http://localhost:8001/docs. Stop only this project with `docker compose down`.

Local Python alternative (saved data already included):

```sh
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.lock.txt
cd backend
../.venv/bin/uvicorn app.main:app --reload --port 8000
```

Offline checks from `backend`: `../.venv/bin/pytest -q` and `../.venv/bin/python -m scripts.verify_raw_selection`. See [frontend-contract.md](frontend-contract.md) for the React handoff.
