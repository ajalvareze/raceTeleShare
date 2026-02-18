from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_superuser
from app.database import get_db
from app.models.track import Track
from app.models.user import User
from app.schemas.track import TrackCreate, TrackOut, TrackUpdate

router = APIRouter(prefix="/tracks", tags=["tracks"])


@router.get("/", response_model=list[TrackOut])
def list_tracks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Track).offset(skip).limit(limit).all()


@router.get("/{track_id}", response_model=TrackOut)
def get_track(track_id: int, db: Session = Depends(get_db)):
    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    return track


@router.post("/", response_model=TrackOut, status_code=201)
def create_track(
    payload: TrackCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    track = Track(**payload.model_dump())
    db.add(track)
    db.commit()
    db.refresh(track)
    return track


@router.patch("/{track_id}", response_model=TrackOut)
def update_track(
    track_id: int,
    payload: TrackUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(track, field, value)
    db.commit()
    db.refresh(track)
    return track
