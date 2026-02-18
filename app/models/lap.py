from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Lap(Base):
    __tablename__ = "laps"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    lap_number: Mapped[int] = mapped_column(Integer, nullable=False)

    lap_time_ms: Mapped[int | None] = mapped_column(Integer)
    sector1_ms: Mapped[int | None] = mapped_column(Integer)
    sector2_ms: Mapped[int | None] = mapped_column(Integer)
    sector3_ms: Mapped[int | None] = mapped_column(Integer)

    # Points to the session-level source file; lap_number identifies the slice
    telemetry_file_path: Mapped[str | None] = mapped_column(String(512))
    telemetry_format: Mapped[str | None] = mapped_column(String(32))

    # Derived metrics
    max_speed_kmh: Mapped[float | None] = mapped_column(Float)
    avg_speed_kmh: Mapped[float | None] = mapped_column(Float)
    max_throttle_pct: Mapped[float | None] = mapped_column(Float)
    max_brake_pct: Mapped[float | None] = mapped_column(Float)
    summary: Mapped[dict | None] = mapped_column(JSON)

    # GPS track for map rendering: list of [time, lat, lon, alt]
    gps_track: Mapped[list | None] = mapped_column(JSON)

    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    is_outlap: Mapped[bool] = mapped_column(Boolean, default=False)
    is_inlap: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    session: Mapped["Session"] = relationship(back_populates="laps")  # noqa: F821
