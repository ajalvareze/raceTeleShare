from sqlalchemy import String, Float, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class TrackConfiguration(Base):
    __tablename__ = "track_configurations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)   # "GP Circuit", "Short"
    length_meters: Mapped[float | None] = mapped_column(Float)
    num_sectors: Mapped[int] = mapped_column(Integer, default=3)
    # Start/finish GPS coords for auto-detection
    start_finish_lat: Mapped[float | None] = mapped_column(Float)
    start_finish_lon: Mapped[float | None] = mapped_column(Float)
    # GeoJSON polyline of the track layout
    layout_data: Mapped[str | None] = mapped_column(String)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    track: Mapped["Track"] = relationship(back_populates="configurations")  # noqa: F821
    sessions: Mapped[list["Session"]] = relationship(back_populates="track_configuration")  # noqa: F821
