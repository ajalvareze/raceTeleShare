from sqlalchemy import String, Integer, Float, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.database import Base


class Drivetrain(str, enum.Enum):
    fwd = "FWD"
    rwd = "RWD"
    awd = "AWD"


class Car(Base):
    __tablename__ = "cars"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Required
    make: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)

    # Optional performance fields
    year: Mapped[int | None] = mapped_column(Integer)
    category: Mapped[str | None] = mapped_column(String(64))      # GT3, Touring, Formula…
    drivetrain: Mapped[Drivetrain | None] = mapped_column(Enum(Drivetrain))
    power_hp: Mapped[int | None] = mapped_column(Integer)
    weight_kg: Mapped[int | None] = mapped_column(Integer)
    engine_cc: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(String(1024))

    owner: Mapped["User"] = relationship(back_populates="cars")  # noqa: F821
    sessions: Mapped[list["Session"]] = relationship(back_populates="car")  # noqa: F821
