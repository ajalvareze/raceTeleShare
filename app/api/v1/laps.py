import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.lap import Lap
from app.models.session import Session
from app.models.user import User
from app.schemas.lap import LapCreate, LapOut, LapCompareRequest
from app.schemas.telemetry import CompareResult, TelemetryData, TelemetryChannel
from app.services.storage import save_telemetry_file
from app.services.telemetry.parser import parse
from app.services.telemetry.processor import extract_lap_summary
from app.services.telemetry.comparator import compare_laps, speed_to_distance_m

router = APIRouter(prefix="/laps", tags=["laps"])
settings = get_settings()


def _assert_session_access(session: Session | None, user: User) -> Session:
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.is_public and session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return session


@router.get("/session/{session_id}", response_model=list[LapOut])
def list_laps(
    session_id: int,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.get(Session, session_id)
    _assert_session_access(session, current_user)
    return (
        db.query(Lap)
        .filter(Lap.session_id == session_id)
        .order_by(Lap.lap_number)
        .all()
    )


@router.get("/{lap_id}/telemetry", response_model=TelemetryData)
def get_lap_telemetry(
    lap_id: int,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lap = db.get(Lap, lap_id)
    if not lap:
        raise HTTPException(status_code=404, detail="Lap not found")
    _assert_session_access(db.get(Session, lap.session_id), current_user)

    if not lap.telemetry_file_path or not lap.telemetry_format:
        raise HTTPException(status_code=404, detail="No telemetry data for this lap")

    all_laps = parse(lap.telemetry_file_path, lap.telemetry_format)
    lap_data = next((d for d in all_laps if d["lap_number"] == lap.lap_number), None)
    if not lap_data and all_laps:
        lap_data = all_laps[0]
    if not lap_data:
        raise HTTPException(status_code=404, detail="Lap not found in telemetry file")

    channels = [
        TelemetryChannel(
            name=name,
            unit=ch.get("unit"),
            data=ch["data"],
            timestamps=ch["timestamps"],
        )
        for name, ch in lap_data["channels"].items()
    ]

    # Compute cumulative distance from speed_gps (or speed_obd)
    speed_ch = (lap_data["channels"].get("speed_gps")
                or lap_data["channels"].get("speed_obd"))
    distance_m: list[float] | None = None
    if speed_ch and speed_ch.get("data") and speed_ch.get("timestamps"):
        distance_m = speed_to_distance_m(speed_ch["timestamps"], speed_ch["data"])

    return TelemetryData(
        lap_id=lap.id,
        lap_time_ms=lap.lap_time_ms,
        sample_rate_hz=lap_data.get("sample_rate_hz"),
        channels=channels,
        gps_track=lap.gps_track or lap_data.get("gps_track"),
        distance_m=distance_m,
    )


@router.get("/{lap_id}", response_model=LapOut)
def get_lap(
    lap_id: int,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lap = db.get(Lap, lap_id)
    if not lap:
        raise HTTPException(status_code=404, detail="Lap not found")
    _assert_session_access(db.get(Session, lap.session_id), current_user)
    return lap


@router.post("/", response_model=LapOut, status_code=201)
def create_lap(
    payload: LapCreate,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.get(Session, payload.session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    lap = Lap(**payload.model_dump())
    db.add(lap)
    db.commit()
    db.refresh(lap)
    return lap


@router.post("/{lap_id}/upload", response_model=LapOut)
async def upload_telemetry(
    lap_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lap = db.get(Lap, lap_id)
    if not lap:
        raise HTTPException(status_code=404, detail="Lap not found")
    session = db.get(Session, lap.session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in settings.allowed_telemetry_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    file_path = await save_telemetry_file(file, lap_id)
    lap.telemetry_file_path = file_path
    lap.telemetry_format = ext.lstrip(".")
    db.commit()

    # Process telemetry in background to extract summary metrics
    background_tasks.add_task(extract_lap_summary, lap_id, file_path, ext)

    db.refresh(lap)
    return lap


@router.post("/compare", response_model=CompareResult)
def compare(
    payload: LapCompareRequest,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if len(payload.lap_ids) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 lap IDs to compare")

    laps = []
    for lap_id in payload.lap_ids:
        lap = db.get(Lap, lap_id)
        if not lap:
            raise HTTPException(status_code=404, detail=f"Lap {lap_id} not found")
        session = db.get(Session, lap.session_id)
        _assert_session_access(session, current_user)
        laps.append(lap)

    return compare_laps(laps, channels=payload.channels)


@router.delete("/{lap_id}", status_code=204)
def delete_lap(
    lap_id: int,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lap = db.get(Lap, lap_id)
    if not lap:
        raise HTTPException(status_code=404, detail="Lap not found")
    session = db.get(Session, lap.session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    db.delete(lap)
    db.commit()
