from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_superuser
from app.database import get_db
from app.models.lap import Lap
from app.models.session import Session as SessionModel
from app.models.track import Track
from app.models.track_configuration import TrackConfiguration
from app.models.user import User

router = APIRouter(prefix="/tracks", tags=["tracks"])


@router.get("/")
def list_tracks(db: Session = Depends(get_db)):
    tracks = db.query(Track).order_by(Track.name).all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "country": t.country,
            "city": t.city,
            "configurations": [
                {"id": c.id, "name": c.name, "length_meters": c.length_meters, "is_default": c.is_default}
                for c in t.configurations
            ],
        }
        for t in tracks
    ]


@router.get("/{track_id}")
def get_track(track_id: int, db: Session = Depends(get_db)):
    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    configs = []
    for c in track.configurations:
        best_lap = (
            db.query(Lap)
            .join(SessionModel, SessionModel.id == Lap.session_id)
            .filter(
                SessionModel.track_configuration_id == c.id,
                SessionModel.is_public == True,   # noqa: E712
                Lap.is_valid == True,             # noqa: E712
                Lap.is_outlap == False,           # noqa: E712
                Lap.is_inlap == False,            # noqa: E712
                Lap.lap_time_ms.isnot(None),
                Lap.gps_track.isnot(None),
            )
            .order_by(Lap.lap_time_ms)
            .first()
        )
        configs.append({
            "id": c.id, "name": c.name, "length_meters": c.length_meters,
            "num_sectors": c.num_sectors, "is_default": c.is_default,
            "start_finish_lat": c.start_finish_lat, "start_finish_lon": c.start_finish_lon,
            "layout_data": c.layout_data,
            "best_lap_gps": best_lap.gps_track if best_lap else None,
        })
    return {
        "id": track.id, "name": track.name, "country": track.country, "city": track.city,
        "configurations": configs,
    }


@router.post("/", status_code=201)
def create_track(payload: dict, db: Session = Depends(get_db), _: User = Depends(get_current_superuser)):
    track = Track(name=payload["name"], country=payload.get("country", ""), city=payload.get("city"))
    db.add(track)
    db.flush()
    config = TrackConfiguration(
        track_id=track.id,
        name=payload.get("configuration_name", "Main Circuit"),
        length_meters=payload.get("length_meters"),
        num_sectors=payload.get("num_sectors", 3),
        start_finish_lat=payload.get("start_finish_lat"),
        start_finish_lon=payload.get("start_finish_lon"),
        is_default=True,
    )
    db.add(config)
    db.commit()
    db.refresh(track)
    return {"id": track.id, "name": track.name, "configuration_id": config.id}


@router.post("/{track_id}/configurations", status_code=201)
def add_configuration(
    track_id: int, payload: dict,
    db: Session = Depends(get_db), _: User = Depends(get_current_superuser),
):
    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    config = TrackConfiguration(
        track_id=track_id,
        name=payload["name"],
        length_meters=payload.get("length_meters"),
        num_sectors=payload.get("num_sectors", 3),
        start_finish_lat=payload.get("start_finish_lat"),
        start_finish_lon=payload.get("start_finish_lon"),
        layout_data=payload.get("layout_data"),
        is_default=payload.get("is_default", False),
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return {"id": config.id, "name": config.name}


@router.patch("/configurations/{config_id}", status_code=200)
def update_configuration(
    config_id: int, payload: dict,
    db: Session = Depends(get_db), _: User = Depends(get_current_superuser),
):
    config = db.get(TrackConfiguration, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    for field in ("name", "length_meters", "num_sectors", "start_finish_lat",
                  "start_finish_lon", "layout_data", "is_default"):
        if field in payload:
            setattr(config, field, payload[field])
    db.commit()
    return {"ok": True}
