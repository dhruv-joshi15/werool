import json
import os
from pathlib import Path
from datetime import date, timedelta
from functools import lru_cache
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from .analysis import FIRST, LAST, decision, metrics, timestamp, iso
from .schemas import Decision, Accuracy, Health, Metadata, Vintages

app = FastAPI(title="Wind forecast historical analysis", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()], allow_methods=["GET"], allow_headers=["*"])
# A service bundle contains backend/data; a checkout keeps the source snapshot at root/data.
# Resolve from this module, never from the process working directory. Docker sets DATA_DIR=/data.
def default_data_dir():
    backend_root = Path(__file__).resolve().parents[1]
    source = backend_root.parent / "data"
    bundled = backend_root / "data"
    return source if (source / "manifest.json").is_file() else bundled

DATA_DIR = Path(os.getenv("DATA_DIR", str(default_data_dir())))

@lru_cache(maxsize=1)
def load_snapshot():
    try:
        manifest = json.loads((DATA_DIR / "manifest.json").read_text())
        import hashlib
        blob = (DATA_DIR / "processed" / (manifest["snapshot_id"] + ".json")).read_bytes()
        if hashlib.sha256(blob).hexdigest() != manifest["snapshot_id"]:
            raise ValueError("Checksum mismatch")
        snapshot = json.loads(blob)
        if not isinstance(snapshot["forecasts"], list) or not isinstance(snapshot["actuals"], list):
            raise ValueError("Invalid snapshot")
        return snapshot, manifest
    except (OSError, ValueError, KeyError, TypeError):
        raise HTTPException(503, "Historical snapshot unavailable or invalid; run ingestion and restart the backend") from None

def scope(day):
    if not FIRST <= day <= LAST:
        raise HTTPException(422, "Decision date must be within January 2026")
    return day

Cutoff = Query(default="10:00", pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")

@app.get("/api/v1/health", response_model=Health)
def health():
    try:
        _, manifest = load_snapshot()
        return dict(service="ok", dataset_ready=True, snapshot_id=manifest["snapshot_id"])
    except HTTPException:
        return dict(service="ok", dataset_ready=False, snapshot_id=None)

@app.get("/api/v1/metadata", response_model=Metadata)
def metadata():
    _, manifest = load_snapshot()
    return dict(actual_interval_minutes=30, alignment_limitation="Timestamp equality does not establish identical measurement intervals: each actual is the half-hour settlement-period MW value starting at that timestamp, not a full-hour average. Forecast interval semantics remain unverified.", coverage_denominator="Expected hourly targets within the requested local delivery days (24 per January decision date; 744 for all 31 dates)", supported_decision_dates={"from": str(FIRST), "to": str(LAST)}, timezone="Europe/London", default_cutoff="10:00", evaluation_resolution_minutes=60, alignment_policy="exact_timestamp_hourly_subset_no_interpolation", assumptions=["10:00 is illustrative, not a verified auction deadline", "Hourly exact matches compare forecast targets with half-hour outturn starting at the same timestamp; this is not whole-day energy accuracy", "Actuals are retrieved historical values; conflicts are quarantined", "Forecast interval semantics and API maximum range remain unresolved"], snapshot=manifest)

@app.get("/api/v1/decision", response_model=Decision, response_model_exclude_unset=True)
def get_decision(date: date, cutoff: str = Cutoff):
    scope(date)
    return decision(load_snapshot()[0], date, cutoff)

@app.get("/api/v1/evaluation", response_model=Decision, response_model_exclude_unset=True)
def get_evaluation(date: date, cutoff: str = Cutoff):
    scope(date)
    return decision(load_snapshot()[0], date, cutoff, True)

@app.get("/api/v1/accuracy", response_model=Accuracy)
def accuracy(from_date: date = Query(alias="from"), to_date: date = Query(alias="to"), cutoff: str = Cutoff):
    scope(from_date); scope(to_date)
    if from_date > to_date:
        raise HTTPException(422, "from must be on or before to")
    snapshot, _ = load_snapshot()
    daily = [decision(snapshot, from_date+timedelta(days=i), cutoff, True) for i in range((to_date-from_date).days+1)]
    return dict(from_date=str(from_date), to_date=str(to_date), cutoff=cutoff, metrics=metrics([r for d in daily for r in d["observations"]]), daily=daily)

@app.get("/api/v1/forecast-vintages", response_model=Vintages)
def vintages(start_time: str):
    try:
        target = timestamp(start_time)
    except (ValueError, TypeError):
        raise HTTPException(422, "start_time must be an ISO timestamp including timezone") from None
    if not date(2026, 1, 2) <= target.date() <= date(2026, 2, 1):
        raise HTTPException(422, "Target outside supported delivery scope")
    return dict(start_time=iso(target), vintages=[r for r in load_snapshot()[0]["forecasts"] if r["start_time"] == iso(target)])
