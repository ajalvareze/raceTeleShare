from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_superuser
from app.database import get_db
from app.models.lap import Lap
from app.models.session import Session as SessionModel
from app.models.track import Track
from app.models.user import User
from app.models.event import Event
from app.services.storage import delete_file

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _: User = Depends(get_current_superuser)):
    return {
        "users": db.query(User).count(),
        "sessions": db.query(SessionModel).count(),
        "laps": db.query(Lap).count(),
        "public_sessions": db.query(SessionModel).filter(SessionModel.is_public == True).count(),  # noqa: E712
        "events": db.query(Event).count(),
    }


@router.get("/users")
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), _: User = Depends(get_current_superuser)):
    users = db.query(User).offset(skip).limit(limit).all()
    return [{"id": u.id, "username": u.username, "email": u.email,
             "is_active": u.is_active, "is_superuser": u.is_superuser,
             "created_at": u.created_at} for u in users]


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_superuser)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    db.delete(user)
    db.commit()


@router.patch("/users/{user_id}/deactivate", status_code=200)
def deactivate_user(user_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_superuser)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    user.is_active = False
    db.commit()
    return {"ok": True}


@router.get("/sessions")
def list_sessions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), _: User = Depends(get_current_superuser)):
    sessions = db.query(SessionModel).order_by(SessionModel.created_at.desc()).offset(skip).limit(limit).all()
    return [{"id": s.id, "user_id": s.user_id, "is_public": s.is_public,
             "date": s.date, "app_source": s.app_source, "vehicle_hint": s.vehicle_hint} for s in sessions]


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_superuser)):
    session = db.get(SessionModel, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.source_file_path:
        delete_file(session.source_file_path)
    db.delete(session)
    db.commit()


@router.get("/events")
def list_events(db: Session = Depends(get_db), _: User = Depends(get_current_superuser)):
    events = db.query(Event).order_by(Event.created_at.desc()).all()
    return [{"id": e.id, "name": e.name, "status": e.status,
             "organizer_id": e.organizer_id, "date_start": e.date_start} for e in events]


@router.delete("/events/{event_id}", status_code=204)
def delete_event(event_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_superuser)):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(event)
    db.commit()


@router.get("/tracks")
def list_tracks(db: Session = Depends(get_db), _: User = Depends(get_current_superuser)):
    tracks = db.query(Track).order_by(Track.name).all()
    return [{"id": t.id, "name": t.name, "country": t.country, "city": t.city} for t in tracks]


@router.patch("/tracks/{track_id}", status_code=200)
def update_track(track_id: int, payload: dict, db: Session = Depends(get_db), _: User = Depends(get_current_superuser)):
    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    for field in ("name", "country", "city"):
        if field in payload:
            setattr(track, field, payload[field])
    db.commit()
    return {"ok": True}
