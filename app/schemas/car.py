from pydantic import BaseModel


class CarBase(BaseModel):
    make: str
    model: str
    year: int | None = None
    category: str | None = None
    drivetrain: str | None = None
    power_hp: int | None = None
    weight_kg: int | None = None
    engine_cc: int | None = None
    notes: str | None = None


class CarCreate(CarBase):
    pass


class CarUpdate(BaseModel):
    make: str | None = None
    model: str | None = None
    year: int | None = None
    category: str | None = None
    drivetrain: str | None = None
    power_hp: int | None = None
    weight_kg: int | None = None
    engine_cc: int | None = None
    notes: str | None = None


class CarOut(CarBase):
    id: int
    owner_id: int

    model_config = {"from_attributes": True}
