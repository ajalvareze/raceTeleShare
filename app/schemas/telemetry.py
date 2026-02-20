from pydantic import BaseModel


class TelemetryChannel(BaseModel):
    name: str
    unit: str | None = None
    data: list[float]
    timestamps: list[float]  # x-axis: seconds (single lap) or meters (compare)


class TelemetryData(BaseModel):
    lap_id: int
    lap_time_ms: int | None = None
    sample_rate_hz: float | None = None
    channels: list[TelemetryChannel]
    gps_track: list[list[float]] | None = None  # [[time, lat, lon, alt], ...]
    distance_m: list[float] | None = None  # cumulative distance per sample (meters)


class LapDelta(BaseModel):
    """Time delta between two laps at each distance point."""
    reference_lap_id: int
    comparison_lap_id: int
    timestamps: list[float]  # distance axis (meters)
    delta_seconds: list[float]  # positive = comparison is slower


class CompareResult(BaseModel):
    laps: list[TelemetryData]
    deltas: list[LapDelta]  # pairwise deltas vs first lap
    channels_available: list[str]
