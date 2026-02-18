"""
Parses a session-level telemetry file and creates Lap records in the database.
Called as a BackgroundTask after session upload.
"""
from __future__ import annotations

import logging
import os

from app.database import SessionLocal
from app.models.lap import Lap
from app.models.session import Session
from app.services.telemetry.parser import parse

logger = logging.getLogger(__name__)


def import_session_laps(session_id: int, file_path: str, fmt: str) -> None:
    db = SessionLocal()
    try:
        session = db.get(Session, session_id)
        if not session:
            return

        laps_data = parse(file_path, fmt)

        for lap_data in laps_data:
            lap_number = lap_data["lap_number"]
            existing = db.query(Lap).filter_by(session_id=session_id, lap_number=lap_number).first()
            if existing:
                lap = existing
            else:
                lap = Lap(session_id=session_id, lap_number=lap_number)
                db.add(lap)

            lap.lap_time_ms = lap_data.get("lap_time_ms")
            lap.telemetry_file_path = file_path
            lap.telemetry_format = fmt
            lap.gps_track = lap_data.get("gps_track") or []
            lap.is_outlap = lap_data.get("is_outlap", False)
            lap.is_inlap = lap_data.get("is_inlap", False)
            lap.is_valid = not lap.is_outlap and not lap.is_inlap

            channels = lap_data.get("channels", {})
            speed = channels.get("speed_gps") or channels.get("speed_obd")
            if speed and speed["data"]:
                lap.max_speed_kmh = round(max(speed["data"]), 1)
                lap.avg_speed_kmh = round(sum(speed["data"]) / len(speed["data"]), 1)

            throttle = channels.get("throttle")
            if throttle and throttle["data"]:
                lap.max_throttle_pct = round(max(throttle["data"]), 1)

            brake = channels.get("brake")
            if brake and brake["data"]:
                lap.max_brake_pct = round(max(brake["data"]), 1)

            lap.summary = {
                name: {
                    "min": round(min(ch["data"]), 3) if ch["data"] else None,
                    "max": round(max(ch["data"]), 3) if ch["data"] else None,
                    "avg": round(sum(ch["data"]) / len(ch["data"]), 3) if ch["data"] else None,
                    "unit": ch.get("unit"),
                }
                for name, ch in channels.items()
            }

        db.commit()
        logger.info("Imported %d laps for session %d", len(laps_data), session_id)
    except Exception:
        logger.exception("Failed to import laps for session %d", session_id)
        db.rollback()
    finally:
        db.close()
