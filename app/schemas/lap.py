from datetime import datetime
from pydantic import BaseModel, model_validator


class LapBase(BaseModel):
    session_id: int
    lap_number: int
    lap_time_ms: int | None = None
    sector1_ms: int | None = None
    sector2_ms: int | None = None
    sector3_ms: int | None = None
    is_valid: bool = True
    is_outlap: bool = False
    is_inlap: bool = False


class LapCreate(LapBase):
    pass


class LapOut(LapBase):
    id: int
    telemetry_file_path: str | None = None
    telemetry_format: str | None = None
    max_speed_kmh: float | None = None
    avg_speed_kmh: float | None = None
    created_at: datetime

    # Formatted lap time for display
    lap_time_display: str | None = None

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def format_lap_time(self) -> "LapOut":
        if self.lap_time_ms is not None:
            total_ms = self.lap_time_ms
            minutes = total_ms // 60000
            seconds = (total_ms % 60000) / 1000
            self.lap_time_display = f"{minutes}:{seconds:06.3f}"
        return self


class LapCompareRequest(BaseModel):
    lap_ids: list[int]
    channels: list[str] | None = None  # specific channels to compare; None = all
