from pydantic import BaseModel

class Metrics(BaseModel):
    status: str
    mae_mw: float | None
    rmse_mw: float | None
    bias_mw: float | None
    matched_count: int
    expected_count: int
    coverage_percent: float | None
    positive_count: int
    negative_count: int
    zero_count: int

class Observation(BaseModel):
    start_time: str
    forecast_mw: float | None
    publish_time: str | None
    forecast_conflict: bool
    forecast_age_hours: float | None
    lead_time_hours: float | None
    actual_mw: float | None = None
    actual_conflict: bool | None = None
    signed_error_mw: float | None = None
    absolute_error_mw: float | None = None

class Decision(BaseModel):
    decision_date: str
    decision_timestamp: str
    delivery_date: str
    cutoff: str
    timezone: str
    evaluation_resolution_minutes: int
    alignment_policy: str
    context: str
    coverage: dict[str, int]
    observations: list[Observation]
    metrics: Metrics | None

class Accuracy(BaseModel):
    from_date: str
    to_date: str
    cutoff: str
    metrics: Metrics
    daily: list[Decision]

class Health(BaseModel):
    service: str
    dataset_ready: bool
    snapshot_id: str | None

class Metadata(BaseModel):
    actual_interval_minutes: int
    alignment_limitation: str
    coverage_denominator: str
    supported_decision_dates: dict[str, str]
    timezone: str
    default_cutoff: str
    evaluation_resolution_minutes: int
    alignment_policy: str
    assumptions: list[str]
    snapshot: dict

class Vintage(BaseModel):
    start_time: str
    publish_time: str
    generation_mw: float | None
    conflict: bool

class Vintages(BaseModel):
    start_time: str
    vintages: list[Vintage]
