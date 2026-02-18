from datetime import datetime
from pydantic import BaseModel
from app.models.session import SessionType


class SessionBase(BaseModel):
    track_id: int
    car_id: int | None = None
    session_type: SessionType = SessionType.practice
    date: datetime
    notes: str | None = None
    is_public: bool = False


class SessionCreate(SessionBase):
    pass


class SessionUpdate(BaseModel):
    notes: str | None = None
    is_public: bool | None = None
    session_type: SessionType | None = None


class SessionOut(SessionBase):
    id: int
    user_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
