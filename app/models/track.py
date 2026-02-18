from sqlalchemy import String, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(64))
    city: Mapped[str | None] = mapped_column(String(64))
    length_meters: Mapped[float | None] = mapped_column(Float)
    num_sectors: Mapped[int] = mapped_column(Integer, default=3)
    # Track layout coordinates (GeoJSON string or similar)
    layout_data: Mapped[str | None] = mapped_column(String)

    sessions: Mapped[list["Session"]] = relationship(back_populates="track")  # noqa: F821
