"""
Post-upload telemetry processing.
Runs as a background task after a file is uploaded.
"""
from __future__ import annotations

import logging
from app.database import SessionLocal
from app.models.lap import Lap
from app.services.telemetry.parser import parse

logger = logging.getLogger(__name__)


def extract_lap_summary(lap_id: int, file_path: str, fmt: str) -> None:
    """Parse telemetry and update the Lap row with derived metrics."""
    db = SessionLocal()
    try:
        lap = db.get(Lap, lap_id)
        if not lap:
            return

        data = parse(file_path, fmt)
        channels = data.get("channels", {})

        if data.get("lap_time_ms"):
            lap.lap_time_ms = data["lap_time_ms"]

        speed_ch = _find_channel(channels, ["speed", "Speed", "GPS Speed", "vCar"])
        if speed_ch:
            values = speed_ch["data"]
            lap.max_speed_kmh = max(values) if values else None
            lap.avg_speed_kmh = sum(values) / len(values) if values else None

        throttle_ch = _find_channel(channels, ["throttle", "Throttle", "nThrottle"])
        if throttle_ch:
            lap.max_throttle_pct = max(throttle_ch["data"]) if throttle_ch["data"] else None

        brake_ch = _find_channel(channels, ["brake", "Brake", "nBrake"])
        if brake_ch:
            lap.max_brake_pct = max(brake_ch["data"]) if brake_ch["data"] else None

        # Store a lightweight summary
        lap.summary = {
            name: {
                "min": min(ch["data"]) if ch["data"] else None,
                "max": max(ch["data"]) if ch["data"] else None,
                "avg": sum(ch["data"]) / len(ch["data"]) if ch["data"] else None,
                "unit": ch.get("unit"),
            }
            for name, ch in channels.items()
        }

        db.commit()
    except Exception:
        logger.exception("Failed to process telemetry for lap %s", lap_id)
        db.rollback()
    finally:
        db.close()


def _find_channel(channels: dict, candidates: list[str]) -> dict | None:
    for name in candidates:
        if name in channels:
            return channels[name]
    return None
