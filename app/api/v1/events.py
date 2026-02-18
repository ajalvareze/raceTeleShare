from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_current_user, get_optional_user
from app.database import get_db
from app.models.event import Event, EventParticipant, EventStatus
from app.models.session import Session
from app.models.user import User

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/")
def list_events(db: DbSession = Depends(get_db)):
    events = (
        db.query(Event)
        .filter(Event.is_public == True, Event.status != EventStatus.completed)  # noqa: E712
        .order_by(Event.date_start)
        .all()
    )
    return [_event_summary(e, db) for e in events]


@router.get("/{event_id}")
def get_event(event_id: int, db: DbSession = Depends(get_db), current_user: User | None = Depends(get_optional_user)):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not event.is_public and (not current_user or current_user.id != event.organizer_id):
        raise HTTPException(status_code=403, detail="Access denied")
    return _event_detail(event, db)


@router.post("/", status_code=201)
def create_event(
    payload: dict,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = Event(
        organizer_id=current_user.id,
        track_configuration_id=payload["track_configuration_id"],
        name=payload["name"],
        description=payload.get("description"),
        date_start=datetime.fromisoformat(payload["date_start"]),
        date_end=datetime.fromisoformat(payload["date_end"]),
        is_public=payload.get("is_public", True),
        is_open=payload.get("is_open", True),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return {"id": event.id, "name": event.name}


@router.post("/{event_id}/join", status_code=201)
def join_event(event_id: int, db: DbSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not event.is_open:
        raise HTTPException(status_code=403, detail="Event is invite-only")
    if event.status == EventStatus.completed:
        raise HTTPException(status_code=400, detail="Event has ended")
    existing = db.query(EventParticipant).filter_by(event_id=event_id, user_id=current_user.id).first()
    if existing:
        return {"ok": True, "already_joined": True}
    db.add(EventParticipant(event_id=event_id, user_id=current_user.id))
    db.commit()
    return {"ok": True}


@router.patch("/{event_id}/status")
def update_event_status(
    event_id: int,
    payload: dict,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = db.get(Event, event_id)
    if not event or event.organizer_id != current_user.id:
        raise HTTPException(status_code=404, detail="Event not found")
    event.status = EventStatus(payload["status"])
    db.commit()
    return {"ok": True}


def _event_summary(event: Event, db: DbSession) -> dict:
    participant_count = db.query(EventParticipant).filter_by(event_id=event.id).count()
    return {
        "id": event.id,
        "name": event.name,
        "status": event.status,
        "date_start": event.date_start,
        "date_end": event.date_end,
        "is_open": event.is_open,
        "participant_count": participant_count,
        "track_configuration_id": event.track_configuration_id,
    }


def _event_detail(event: Event, db: DbSession) -> dict:
    from app.models.lap import Lap
    from sqlalchemy import func

    leaderboard = (
        db.query(
            User.username,
            func.min(Lap.lap_time_ms).label("best_ms"),
        )
        .join(Session, Session.user_id == User.id)
        .join(Lap, Lap.session_id == Session.id)
        .filter(
            Session.event_id == event.id,
            Lap.is_valid == True,   # noqa: E712
            Lap.is_outlap == False, # noqa: E712
            Lap.is_inlap == False,  # noqa: E712
            Lap.lap_time_ms.isnot(None),
        )
        .group_by(User.username)
        .order_by(func.min(Lap.lap_time_ms))
        .all()
    )

    return {
        **_event_summary(event, db),
        "description": event.description,
        "leaderboard": [
            {"rank": i + 1, "username": r.username, "best_lap_display": _fmt(r.best_ms)}
            for i, r in enumerate(leaderboard)
        ],
    }


def _fmt(ms: int | None) -> str | None:
    if ms is None:
        return None
    m = ms // 60000
    s = (ms % 60000) / 1000
    return f"{m}:{s:06.3f}"
