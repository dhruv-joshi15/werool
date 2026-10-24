"""Explicit network ingestion; never called from API handlers."""
import argparse
import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import httpx
from app.analysis import normalize, timestamp, iso

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"

def fetch(client, dataset, params):
    url = f"{BASE}/{dataset}/stream"
    for attempt in range(4):
        try:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                raise ValueError(f"Unexpected response format from {url}")
            # Detect ignored publication filters rather than trusting the request.
            lo, hi = timestamp(params["publishDateTimeFrom"]), timestamp(params["publishDateTimeTo"])
            if any(not lo <= timestamp(r["publishTime"]) <= hi for r in data):
                raise ValueError(f"Publication filter not respected by {url}")
            return data, str(response.url)
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500 and exc.response.status_code != 429:
                raise RuntimeError(f"Elexon request failed: {exc}") from exc
            if attempt == 3:
                raise RuntimeError(f"Elexon request failed after four attempts: {exc}") from exc
            time.sleep(2**attempt)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parents[2]/"data")
    args = parser.parse_args()
    root = args.data_dir
    run = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    raw_dir = root/"raw"/run
    raw_dir.mkdir(parents=True)
    (root/"processed").mkdir(parents=True, exist_ok=True)
    requests, normalized, quality = [], {}, {}
    with httpx.Client(timeout=httpx.Timeout(60, connect=15), follow_redirects=True) as client:
        for dataset, begin, end, key in [("WINDFOR", "2025-12-25", "2026-02-01", "forecasts"), ("FUELHH", "2026-01-01", "2026-02-04", "actuals")]:
            current, stop = timestamp(begin+"T00:00:00Z"), timestamp(end+"T00:00:00Z")
            records = []
            while current < stop:
                next_day = min(current+timedelta(days=1), stop)
                params = {"publishDateTimeFrom": iso(current), "publishDateTimeTo": iso(next_day)}
                rows, url = fetch(client, dataset, params)
                name = f"{dataset}-{current:%Y-%m-%d}.json"
                blob = json.dumps(rows, separators=(",", ":")).encode()
                (raw_dir/name).write_bytes(blob)
                requests.append(dict(url=url, parameters=params, retrieved_at=iso(datetime.now(timezone.utc)), row_count=len(rows), raw_file=f"raw/{run}/{name}", sha256=hashlib.sha256(blob).hexdigest()))
                records.extend(rows)
                print(f"{dataset} {current.date()}: {len(rows)} rows", flush=True)
                current = next_day
            clean, issues = normalize(records, key == "forecasts")
            normalized[key] = [r for r in clean if "2026-01-02T00:00:00Z" <= r["start_time"] < "2026-02-02T00:00:00Z"]
            quality[key] = issues
    blob = json.dumps(normalized, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    identity = hashlib.sha256(blob).hexdigest()
    (root/"processed"/(identity+".json")).write_bytes(blob)
    manifest = dict(snapshot_id=identity, retrieved_at=iso(datetime.now(timezone.utc)), requests=requests, quality=quality, row_counts={k: len(v) for k,v in normalized.items()}, coverage={k: {"first_target": min((r["start_time"] for r in v), default=None), "last_target": max((r["start_time"] for r in v), default=None)} for k,v in normalized.items()}, limitations=["One-week publication warm-up is bounded; absent eligible forecasts remain missing", "Actual publications retrieved through February 3; later revisions are not included", "One-day stream requests; API maximum range and truncation guarantees unverified"])
    temporary = root/"manifest.pending.json"
    temporary.write_text(json.dumps(manifest, indent=2))
    temporary.replace(root/"manifest.json")
    print(f"Snapshot ready: {identity}")

if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, KeyError) as exc:
        raise SystemExit(f"Ingestion failed: {exc}") from None
