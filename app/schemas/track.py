from pydantic import BaseModel


class TrackBase(BaseModel):
    name: str
    country: str
    city: str | None = None
    length_meters: float | None = None
    num_sectors: int = 3


class TrackCreate(TrackBase):
    layout_data: str | None = None


class TrackUpdate(BaseModel):
    name: str | None = None
    country: str | None = None
    city: str | None = None
    length_meters: float | None = None
    num_sectors: int | None = None
    layout_data: str | None = None


class TrackOut(TrackBase):
    id: int

    model_config = {"from_attributes": True}
