from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.lap import Lap
from app.models.session import Session as SessionModel
from app.models.track_configuration import TrackConfiguration
from app.models.track import Track
from app.models.user import User
from app.models.car import Car

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("/")
def list_active_tracks(db: Session = Depends(get_db)):
    """All tracks that have at least one public timed lap."""
    rows = (
        db.query(Track, TrackConfiguration, func.min(Lap.lap_time_ms).label("best_ms"))
        .join(TrackConfiguration, TrackConfiguration.track_id == Track.id)
        .join(SessionModel, SessionModel.track_configuration_id == TrackConfiguration.id)
        .join(Lap, Lap.session_id == SessionModel.id)
        .filter(
            SessionModel.is_public == True,  # noqa: E712
            Lap.is_valid == True,            # noqa: E712
            Lap.is_outlap == False,          # noqa: E712
            Lap.is_inlap == False,           # noqa: E712
            Lap.lap_time_ms.isnot(None),
        )
        .group_by(Track.id, TrackConfiguration.id)
        .order_by(Track.name, TrackConfiguration.name)
        .all()
    )
    return [
        {
            "track_id": track.id,
            "track_name": track.name,
            "country": track.country,
            "configuration_id": config.id,
            "configuration_name": config.name,
            "best_lap_ms": best_ms,
            "best_lap_display": _fmt(best_ms),
        }
        for track, config, best_ms in rows
    ]


@router.get("/{configuration_id}")
def leaderboard(configuration_id: int, limit: int = 50, db: Session = Depends(get_db)):
    """Best lap per user for a given track configuration (public sessions only)."""
    config = db.get(TrackConfiguration, configuration_id)
    if not config:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Track configuration not found")

    # Best lap per user
    subq = (
        db.query(
            User.id.label("user_id"),
            User.username,
            User.full_name,
            Car.make.label("car_make"),
            Car.model.label("car_model"),
            Car.year.label("car_year"),
            Car.category.label("car_category"),
            SessionModel.id.label("session_id"),
            SessionModel.date.label("session_date"),
            func.min(Lap.lap_time_ms).label("best_ms"),
            func.max(Lap.max_speed_kmh).label("top_speed"),
        )
        .join(SessionModel, SessionModel.user_id == User.id)
        .outerjoin(Car, Car.id == SessionModel.car_id)
        .join(Lap, Lap.session_id == SessionModel.id)
        .filter(
            SessionModel.track_configuration_id == configuration_id,
            SessionModel.is_public == True,  # noqa: E712
            Lap.is_valid == True,            # noqa: E712
            Lap.is_outlap == False,          # noqa: E712
            Lap.is_inlap == False,           # noqa: E712
            Lap.lap_time_ms.isnot(None),
        )
        .group_by(User.id, User.username, User.full_name,
                  Car.make, Car.model, Car.year, Car.category,
                  SessionModel.id, SessionModel.date)
        .order_by(func.min(Lap.lap_time_ms))
        .limit(limit)
        .all()
    )

    track = db.get(Track, config.track_id)
    return {
        "track": {"id": track.id, "name": track.name, "country": track.country},
        "configuration": {"id": config.id, "name": config.name, "length_meters": config.length_meters},
        "entries": [
            {
                "rank": i + 1,
                "user": {"id": r.user_id, "username": r.username, "full_name": r.full_name},
                "car": f"{r.car_year or ''} {r.car_make or ''} {r.car_model or ''}".strip() or None,
                "car_category": r.car_category,
                "session_id": r.session_id,
                "session_date": r.session_date,
                "best_lap_ms": r.best_ms,
                "best_lap_display": _fmt(r.best_ms),
                "top_speed_kmh": r.top_speed,
            }
            for i, r in enumerate(subq)
        ],
    }


def _fmt(ms: int | None) -> str | None:
    if ms is None:
        return None
    m = ms // 60000
    s = (ms % 60000) / 1000
    return f"{m}:{s:06.3f}"
