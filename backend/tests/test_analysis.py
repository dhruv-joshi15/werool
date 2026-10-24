"""All fixtures below are synthetic; no network requests."""
from datetime import date
import json
import pytest
from fastapi.testclient import TestClient
from app.analysis import normalize, decision, metrics
from app.main import app, load_snapshot

def record(target="2026-01-02T00:00:00Z", pub="2026-01-01T10:00:00Z", value=10):
    return dict(startTime=target, publishTime=pub, generation=value)

def test_cutoff_and_independent_selection():
    rows=[record(pub="2026-01-01T09:00:00Z",value=1),record(value=2),record(pub="2026-01-01T10:01:00Z",value=99),record(target="2026-01-02T01:00:00Z",value=0)]
    forecasts,_=normalize(rows,True)
    result=decision(dict(forecasts=forecasts,actuals=[]),date(2026,1,1))
    a,b,c=result["observations"][:3]
    assert a["forecast_mw"]==2 and b["forecast_mw"]==0 and c["forecast_mw"] is None
    assert result["coverage"]["expected_intervals"]==24
    assert "actual_mw" not in a

def test_conflicts_quarantined():
    rows, issues=normalize([record(),record(),record(value=20)],True)
    assert issues["duplicates"]==1 and issues["conflicts"]==1
    assert rows[0]["generation_mw"] is None

def test_zero_invalid_and_missing_resolution():
    actuals,issues=normalize([dict(record(value=0),fuelType="WIND"),dict(record(value=None),fuelType="WIND")],False)
    assert actuals[0]["generation_mw"]==0 and issues["invalid"]==1
    out=decision(dict(forecasts=[],actuals=actuals),date(2026,1,1),evaluate=True)
    assert out["coverage"]["available_actual_intervals"]==1
    assert out["metrics"]["mae_mw"] is None
    json.dumps(out,allow_nan=False)

def test_hand_calculated_metrics():
    rows=[{"signed_error_mw":3},{"signed_error_mw":-4},{"signed_error_mw":0},{"signed_error_mw":None}]
    result=metrics(rows)
    assert result["mae_mw"]==pytest.approx(7/3)
    assert result["rmse_mw"]==pytest.approx((25/3)**.5)
    assert result["bias_mw"]==pytest.approx(-1/3)
    assert result["coverage_percent"]==75

def test_month_boundary():
    result=decision(dict(forecasts=[],actuals=[]),date(2026,1,31))
    assert result["delivery_date"]=="2026-02-01"
    assert len(result["observations"])==24

def test_api_validation_and_unavailable(monkeypatch,tmp_path):
    import app.main as main
    monkeypatch.setattr(main,"DATA_DIR",tmp_path)
    load_snapshot.cache_clear()
    client=TestClient(app)
    assert client.get("/api/v1/health").json()["dataset_ready"] is False
    assert client.get("/api/v1/metadata").status_code==503
    assert client.get("/api/v1/evaluation?date=bad").status_code==422
    assert client.get("/api/v1/evaluation?date=2026-01-01&cutoff=25:00").status_code==422
    assert client.get("/api/v1/accuracy?from=2026-01-20&to=2026-01-01").status_code==422
    load_snapshot.cache_clear()


def test_independent_vintages_missing_and_half_hour_exclusion():
    forecasts, _ = normalize([
        record(pub="2026-01-01T09:00:00Z", value=5),
        record(value=10),
        record(pub="2026-01-01T10:01:00Z", value=999),
        record(target="2026-01-02T01:00:00Z", pub="2026-01-01T08:00:00Z", value=0),
        record(target="2026-01-02T02:00:00Z", value=8),
    ], True)
    actuals, _ = normalize([
        dict(record(value=0), fuelType="WIND"),
        dict(record(target="2026-01-02T00:30:00Z", value=999), fuelType="WIND"),
        dict(record(target="2026-01-02T01:00:00Z", value=0), fuelType="WIND"),
    ], False)
    out = decision(dict(forecasts=forecasts, actuals=actuals), date(2026, 1, 1), evaluate=True)
    assert [r["publish_time"] for r in out["observations"][:2]] == ["2026-01-01T10:00:00Z", "2026-01-01T08:00:00Z"]
    assert out["coverage"]["missing_forecasts"] == 21
    assert out["coverage"]["missing_actuals"] == 22
    assert out["metrics"]["matched_count"] == 2
    assert out["metrics"]["mae_mw"] == 5
    assert out["metrics"]["coverage_percent"] == pytest.approx(100*2/24)
    assert all(not r["start_time"].endswith("30:00Z") for r in out["observations"])


def test_period_api_weights_observations_and_excludes_future(monkeypatch):
    import app.main as main
    raw_f, raw_a = [], []
    for target, pub, value in [
        ("2026-01-02T00:00:00Z", "2026-01-01T10:00:00Z", 10),
        ("2026-01-03T00:00:00Z", "2026-01-02T09:00:00Z", 0),
        ("2026-01-03T01:00:00Z", "2026-01-02T09:30:00Z", 0),
    ]:
        raw_f.extend([record(target,pub,value), record(target,pub[:11]+"11:00:00Z",999)])
        raw_a.append(dict(record(target,pub,0),fuelType="WIND"))
    f,_=normalize(raw_f,True)
    a,_=normalize(raw_a,False)
    monkeypatch.setattr(main,"load_snapshot",lambda: ({"forecasts":f,"actuals":a},{}))
    client=TestClient(app)
    response=client.get("/api/v1/accuracy?from=2026-01-01&to=2026-01-02")
    assert response.status_code==200
    body=response.json()
    assert body["metrics"]["mae_mw"]==pytest.approx(10/3)
    assert body["metrics"]["mae_mw"] != 5  # unweighted daily MAE would be 5
    assert body["metrics"]["rmse_mw"]==pytest.approx((100/3)**.5)
    assert body["metrics"]["expected_count"]==48
    assert body["daily"][0]["metrics"]["mae_mw"]==10


@pytest.mark.parametrize("path",[
    "/api/v1/decision?date=2026-02-01",
    "/api/v1/accuracy?from=2025-12-31&to=2026-01-01",
    "/api/v1/forecast-vintages?start_time=2026-01-02T00:00:00",
    "/api/v1/forecast-vintages?start_time=2026-02-02T00:00:00Z",
    "/api/v1/decision?date=2026-01-01&cutoff=9:00",
])
def test_additional_input_validation(path):
    assert TestClient(app).get(path).status_code==422


def test_timezone_calendar_and_naive_rejection():
    from app.analysis import timestamp, target_grid
    with pytest.raises(ValueError):
        timestamp("2026-01-01T10:00:00")
    assert timestamp("2026-01-01T11:00:00+01:00")==timestamp("2026-01-01T10:00:00Z")
    delivery,grid=target_grid(date(2026,1,1))
    assert delivery==date(2026,1,2) and grid[0].tzinfo is not None
    # Local-calendar boundaries continue to work at the spring clock change.
    assert len(target_grid(date(2026,3,28))[1])==23


def test_malformed_timestamp_is_rejected_as_invalid():
    rows, issues = normalize([dict(record(), startTime=None),dict(record(), publishTime=123)],True)
    assert rows==[] and issues['invalid']==2
