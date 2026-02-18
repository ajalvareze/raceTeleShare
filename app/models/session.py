from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, DateTime, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.database import Base


class SessionType(str, enum.Enum):
    practice = "practice"
    qualifying = "qualifying"
    race = "race"
    hotlap = "hotlap"


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    track_configuration_id: Mapped[int] = mapped_column(ForeignKey("track_configurations.id"), nullable=False)
    car_id: Mapped[int | None] = mapped_column(ForeignKey("cars.id"))
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"))
    session_type: Mapped[SessionType] = mapped_column(Enum(SessionType), default=SessionType.practice)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1024))
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)

    # Source file metadata (populated on upload)
    source_file_path: Mapped[str | None] = mapped_column(String(512))
    app_source: Mapped[str | None] = mapped_column(String(64))    # "trackaddict", "motec"…
    vehicle_hint: Mapped[str | None] = mapped_column(String(128)) # raw vehicle string from file

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship(back_populates="sessions")  # noqa: F821
    track_configuration: Mapped["TrackConfiguration"] = relationship(back_populates="sessions")  # noqa: F821
    car: Mapped["Car"] = relationship(back_populates="sessions")  # noqa: F821
    event: Mapped["Event"] = relationship(back_populates="sessions")  # noqa: F821
    laps: Mapped[list["Lap"]] = relationship(back_populates="session", cascade="all, delete-orphan")  # noqa: F821
