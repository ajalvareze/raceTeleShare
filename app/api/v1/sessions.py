import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.session import Session
from app.models.user import User
from app.schemas.session import SessionCreate, SessionOut, SessionUpdate
from app.services.storage import save_session_file
from app.services.session_importer import import_session_laps

router = APIRouter(prefix="/sessions", tags=["sessions"])
settings = get_settings()


@router.get("/", response_model=list[SessionOut])
def list_sessions(
    public_only: bool = False,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Session)
    if public_only:
        query = query.filter(Session.is_public == True)  # noqa: E712
    else:
        query = query.filter(Session.user_id == current_user.id)
    return query.order_by(Session.date.desc()).all()


@router.get("/{session_id}", response_model=SessionOut)
def get_session(
    session_id: int,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.is_public and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return session


@router.post("/", response_model=SessionOut, status_code=201)
def create_session(
    payload: SessionCreate,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = Session(**payload.model_dump(), user_id=current_user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/upload", response_model=SessionOut, status_code=201)
async def upload_session(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in settings.allowed_telemetry_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    # Parse metadata from file header before saving to get date + vehicle hint
    from app.services.telemetry.parser import _parse_trackaddict_meta  # noqa: PLC0415
    raw_header = b""
    chunk = await file.read(4096)
    raw_header = chunk
    await file.seek(0)

    meta: dict = {}
    header_lines = [l for l in raw_header.decode("utf-8", errors="ignore").splitlines() if l.startswith("#")]
    if header_lines:
        meta = _parse_trackaddict_meta(header_lines)

    # Auto-detect track configuration from GPS (stub — uses first available config if only one)
    from app.models.track_configuration import TrackConfiguration  # noqa: PLC0415
    track_config = db.query(TrackConfiguration).first()
    if not track_config:
        raise HTTPException(status_code=400, detail="No track configurations exist yet. Ask an admin to add tracks.")

    session = Session(
        user_id=current_user.id,
        track_configuration_id=track_config.id,
        date=datetime.now(timezone.utc),
        app_source=meta.get("app", "unknown"),
        vehicle_hint=meta.get("vehicle"),
        is_public=False,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    file_path = await save_session_file(file, session.id)
    session.source_file_path = file_path
    db.commit()

    fmt = ext.lstrip(".")
    background_tasks.add_task(import_session_laps, session.id, file_path, fmt)

    db.refresh(session)
    return session


@router.patch("/{session_id}", response_model=SessionOut)
def update_session(
    session_id: int,
    payload: SessionUpdate,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.get(Session, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(session, field, value)
    db.commit()
    db.refresh(session)
    return session


@router.delete("/{session_id}", status_code=204)
def delete_session(
    session_id: int,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.get(Session, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
