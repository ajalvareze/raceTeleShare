from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, DateTime, Boolean, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.database import Base


class EventStatus(str, enum.Enum):
    upcoming = "upcoming"
    active = "active"
    completed = "completed"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organizer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    track_configuration_id: Mapped[int] = mapped_column(ForeignKey("track_configurations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    date_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    date_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)  # anyone can join
    status: Mapped[EventStatus] = mapped_column(Enum(EventStatus), default=EventStatus.upcoming)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    organizer: Mapped["User"] = relationship(back_populates="organized_events")  # noqa: F821
    track_configuration: Mapped["TrackConfiguration"] = relationship()  # noqa: F821
    participants: Mapped[list["EventParticipant"]] = relationship(back_populates="event", cascade="all, delete-orphan")  # noqa: F821
    sessions: Mapped[list["Session"]] = relationship(back_populates="event")  # noqa: F821


class EventParticipant(Base):
    __tablename__ = "event_participants"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    event: Mapped["Event"] = relationship(back_populates="participants")  # noqa: F821
    user: Mapped["User"] = relationship(back_populates="event_participations")  # noqa: F821
