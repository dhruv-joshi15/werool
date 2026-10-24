"""Pure historical selection and exact timestamp evaluation; all times UTC aware."""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from math import sqrt, isfinite
from collections import defaultdict

LONDON = ZoneInfo("Europe/London")
FIRST, LAST = date(2026, 1, 1), date(2026, 1, 31)
RESOLUTION_MINUTES = 60

def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp must be an ISO string")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return dt.astimezone(timezone.utc)

def iso(dt):
    return dt.isoformat().replace("+00:00", "Z")

def normalize(records, forecast):
    groups, issues = defaultdict(list), {"invalid": 0, "duplicates": 0, "conflicts": 0, "filtered": 0}
    for raw in records:
        if not forecast and raw.get("fuelType") != "WIND":
            issues["filtered"] += 1
            continue
        try:
            target = iso(timestamp(raw["startTime"]))
            value = raw["generation"]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
                raise ValueError("Invalid generation")
            pub = iso(timestamp(raw["publishTime"])) if raw.get("publishTime") else None
            if forecast and pub is None:
                raise ValueError("Missing publication")
            groups[(target, pub if forecast else None)].append({"start_time": target, "publish_time": pub, "generation_mw": float(value)})
        except (ValueError, TypeError, KeyError):
            issues["invalid"] += 1
    result = []
    for (target, pub), rows in groups.items():
        # No verified revision ordering: conflicting values are quarantined.
        values = {r["generation_mw"] for r in rows}
        issues["duplicates"] += len(rows) - len(values)
        conflict = len(values) > 1
        issues["conflicts"] += int(conflict)
        result.append({"start_time": target, "publish_time": pub if forecast else max((r["publish_time"] for r in rows if r["publish_time"]), default=None), "generation_mw": None if conflict else rows[0]["generation_mw"], "conflict": conflict})
    return sorted(result, key=lambda r: (r["start_time"], r["publish_time"] or "")), issues

def target_grid(day):
    delivery = day + timedelta(days=1)
    start = datetime.combine(delivery, time(), LONDON).astimezone(timezone.utc)
    end = datetime.combine(delivery + timedelta(days=1), time(), LONDON).astimezone(timezone.utc)
    points = []
    while start < end:
        points.append(start)
        start += timedelta(minutes=RESOLUTION_MINUTES)
    return delivery, points

def metrics(rows):
    errors = [r["signed_error_mw"] for r in rows if r.get("signed_error_mw") is not None]
    n, total = len(errors), len(rows)
    return {"status": "ok" if n else "no_matched_observations", "mae_mw": sum(map(abs, errors))/n if n else None, "rmse_mw": sqrt(sum(x*x for x in errors)/n) if n else None, "bias_mw": sum(errors)/n if n else None, "matched_count": n, "expected_count": total, "coverage_percent": 100*n/total if total else None, "positive_count": sum(x>0 for x in errors), "negative_count": sum(x<0 for x in errors), "zero_count": sum(x==0 for x in errors)}

def decision(snapshot, day, cutoff="10:00", evaluate=False):
    clock = time.fromisoformat(cutoff)
    at = datetime.combine(day, clock, LONDON).astimezone(timezone.utc)
    delivery, grid = target_grid(day)
    forecasts = defaultdict(list)
    for row in snapshot["forecasts"]:
        if timestamp(row["publish_time"]) <= at:
            forecasts[row["start_time"]].append(row)
    actuals = {r["start_time"]: r for r in snapshot["actuals"]}
    rows = []
    for target in grid:
        key = iso(target)
        f = max(forecasts[key], key=lambda r: timestamp(r["publish_time"]), default=None)
        value = f["generation_mw"] if f else None
        row = {"start_time": key, "forecast_mw": value, "publish_time": f["publish_time"] if f else None, "forecast_conflict": bool(f and f["conflict"]), "forecast_age_hours": (at-timestamp(f["publish_time"])).total_seconds()/3600 if f else None, "lead_time_hours": (target-timestamp(f["publish_time"])).total_seconds()/3600 if f else None}
        if evaluate:
            actual = actuals.get(key)
            av = actual["generation_mw"] if actual else None
            error = value-av if value is not None and av is not None else None
            row.update(actual_mw=av, actual_conflict=bool(actual and actual["conflict"]), signed_error_mw=error, absolute_error_mw=abs(error) if error is not None else None)
        rows.append(row)
    coverage = {"expected_intervals": len(rows), "eligible_forecast_intervals": sum(r["forecast_mw"] is not None for r in rows), "missing_forecasts": sum(r["forecast_mw"] is None for r in rows), "forecast_conflicts": sum(r["forecast_conflict"] for r in rows)}
    if evaluate:
        coverage.update(available_actual_intervals=sum(r["actual_mw"] is not None for r in rows), missing_actuals=sum(r["actual_mw"] is None for r in rows), actual_conflicts=sum(r["actual_conflict"] for r in rows), matched_intervals=sum(r["signed_error_mw"] is not None for r in rows))
    return {"decision_date": day.isoformat(), "decision_timestamp": iso(at), "delivery_date": delivery.isoformat(), "cutoff": cutoff, "timezone": "Europe/London", "evaluation_resolution_minutes": RESOLUTION_MINUTES, "alignment_policy": "exact_timestamp_hourly_subset_no_interpolation", "context": "retrieved_historical_outturn_evaluation" if evaluate else "as_of_decision_no_outcomes", "coverage": coverage, "observations": rows, "metrics": metrics(rows) if evaluate else None}
