from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.session import Session
from app.models.user import User
from app.schemas.session import SessionCreate, SessionOut, SessionUpdate

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/", response_model=list[SessionOut])
def list_sessions(
    public_only: bool = False,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Session)
    if public_only:
        query = query.filter(Session.is_public == True)
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
