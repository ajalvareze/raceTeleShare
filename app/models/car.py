from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Car(Base):
    __tablename__ = "cars"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    make: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    year: Mapped[int | None] = mapped_column(Integer)
    category: Mapped[str | None] = mapped_column(String(64))  # e.g. GT3, Formula, Touring
    notes: Mapped[str | None] = mapped_column(String(512))

    owner: Mapped["User"] = relationship(back_populates="cars")  # noqa: F821
    sessions: Mapped[list["Session"]] = relationship(back_populates="car")  # noqa: F821
