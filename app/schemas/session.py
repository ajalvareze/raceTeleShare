from datetime import datetime
from pydantic import BaseModel
from app.models.session import SessionType


class SessionBase(BaseModel):
    track_configuration_id: int
    car_id: int | None = None
    event_id: int | None = None
    session_type: SessionType = SessionType.practice
    date: datetime
    notes: str | None = None
    is_public: bool = False


class SessionCreate(SessionBase):
    pass


class SessionUpdate(BaseModel):
    track_configuration_id: int | None = None
    car_id: int | None = None
    event_id: int | None = None
    notes: str | None = None
    is_public: bool | None = None
    session_type: SessionType | None = None


class SessionOut(SessionBase):
    id: int
    user_id: int
    source_file_path: str | None = None
    app_source: str | None = None
    vehicle_hint: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
