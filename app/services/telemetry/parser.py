"""
Telemetry file parsers.

Each parser returns a list of lap dicts (session-level files produce multiple laps):
[
  {
    "lap_number": int,
    "lap_time_ms": int | None,
    "channels": {
        "channel_name": {"unit": str|None, "timestamps": [float], "data": [float]}
    },
    "gps_track": [[time, lat, lon, alt], ...],
    "sample_rate_hz": float | None,
    "metadata": {"vehicle": str, "app": str, ...},
  },
  ...
]
"""
from __future__ import annotations

import csv
import io
import json
import re
from collections import defaultdict
from typing import Any


def parse(file_path: str, fmt: str) -> list[dict[str, Any]]:
    parsers = {
        "csv": _parse_csv_auto,
        "json": _parse_json,
        "ld": _parse_motec_ld,
        "drk": _parse_aim_drk,
        "xdrk": _parse_aim_drk,
    }
    parser = parsers.get(fmt.lower())
    if not parser:
        raise ValueError(f"No parser available for format: {fmt}")
    return parser(file_path)


# ── TrackAddict / generic CSV ────────────────────────────────────────────────

# Channel name → (normalised name, unit)
_CHANNEL_MAP = {
    "Speed (Km/h)":                  ("speed_gps",   "km/h"),
    "Vehicle Speed (km/h) *OBD":     ("speed_obd",   "km/h"),
    "Engine Speed (RPM) *OBD":       ("rpm",         "rpm"),
    "Throttle Position (%) *OBD":    ("throttle",    "%"),
    "Brake (calculated)":            ("brake",       ""),
    "Accel X":                       ("accel_lat",   "g"),
    "Accel Y":                       ("accel_lon",   "g"),
    "Accel Z":                       ("accel_vert",  "g"),
    "Intake Manifold Pressure (kPa) *OBD": ("manifold_pressure", "kPa"),
    "Barometric Pressure (kPa)":     ("baro_pressure", "kPa"),
    "Heading":                       ("heading",     "deg"),
    "Altitude (m)":                  ("altitude",    "m"),
}

_PERFORMANCE_CHANNELS = {
    "speed_gps", "speed_obd", "rpm", "throttle", "brake",
    "accel_lat", "accel_lon", "manifold_pressure",
}


def _parse_csv_auto(file_path: str) -> list[dict[str, Any]]:
    with open(file_path, encoding="utf-8-sig") as f:
        raw = f.read()

    lines = raw.splitlines(keepends=True)
    meta_lines = [l for l in lines if l.startswith("#")]
    data_lines = [l for l in lines if not l.startswith("#")]

    metadata = _parse_trackaddict_meta(meta_lines)

    reader = csv.DictReader(io.StringIO("".join(data_lines)))
    rows = [r for r in reader if r.get("Time") and r["Time"].strip()]

    if "Lap" in (reader.fieldnames or []):
        return _split_trackaddict_laps(rows, metadata)
    else:
        return [_generic_csv_lap(rows)]


def _parse_trackaddict_meta(meta_lines: list[str]) -> dict:
    meta: dict[str, Any] = {"app": "trackaddict", "lap_times": {}}
    for line in meta_lines:
        line = line.lstrip("# ").strip()
        if line.startswith("RaceRender Data:"):
            meta["app_version"] = line
        elif line.startswith("Vehicle:"):
            meta["vehicle"] = line.split(":", 1)[1].strip()
        elif m := re.match(r"Lap (\d+): (\d+):(\d+)\.(\d+)", line):
            lap_num = int(m.group(1))
            ms = int(m.group(2)) * 60000 + int(m.group(3)) * 1000 + int(m.group(4))
            meta["lap_times"][lap_num] = ms
    return meta


def _split_trackaddict_laps(rows: list[dict], metadata: dict) -> list[dict[str, Any]]:
    by_lap: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        try:
            by_lap[int(float(r["Lap"]))].append(r)
        except (ValueError, KeyError):
            pass

    laps = []
    lap_nums = sorted(by_lap.keys())
    total_laps = len(lap_nums)

    for idx, lap_num in enumerate(lap_nums):
        lap_rows = by_lap[lap_num]
        t0 = float(lap_rows[0]["Time"])

        channels: dict[str, dict] = {}
        gps_track: list[list] = []

        for raw_name, (norm_name, unit) in _CHANNEL_MAP.items():
            if raw_name not in (lap_rows[0] if lap_rows else {}):
                continue
            ts, vals = [], []
            for r in lap_rows:
                try:
                    ts.append(round(float(r["Time"]) - t0, 4))
                    vals.append(float(r[raw_name]))
                except (ValueError, KeyError):
                    pass
            if ts:
                channels[norm_name] = {"unit": unit, "timestamps": ts, "data": vals}

        for r in lap_rows:
            try:
                gps_track.append([
                    round(float(r["Time"]) - t0, 4),
                    float(r["Latitude"]),
                    float(r["Longitude"]),
                    float(r.get("Altitude (m)", 0)),
                ])
            except (ValueError, KeyError):
                pass

        lap_time_ms = metadata["lap_times"].get(lap_num)
        if lap_time_ms is None and len(lap_rows) >= 2:
            lap_time_ms = int((float(lap_rows[-1]["Time"]) - t0) * 1000)

        ts_vals = channels.get("speed_gps", {}).get("timestamps", [])
        sample_rate = round(len(ts_vals) / ts_vals[-1], 1) if ts_vals and ts_vals[-1] > 0 else None

        laps.append({
            "lap_number": lap_num,
            "lap_time_ms": lap_time_ms,
            "channels": channels,
            "gps_track": gps_track,
            "sample_rate_hz": sample_rate,
            "metadata": metadata,
            "is_outlap": (idx == 0),
            "is_inlap": (idx == total_laps - 1 and total_laps > 2),
        })

    return laps


def _generic_csv_lap(rows: list[dict]) -> dict[str, Any]:
    if not rows:
        return {"lap_number": 0, "lap_time_ms": None, "channels": {}, "gps_track": [], "sample_rate_hz": None, "metadata": {}}
    headers = list(rows[0].keys())
    time_col = headers[0]
    channels: dict[str, dict] = {}
    for col in headers[1:]:
        ts, vals = [], []
        for r in rows:
            try:
                ts.append(float(r[time_col]))
                vals.append(float(r[col]))
            except (ValueError, KeyError):
                pass
        if ts:
            channels[col] = {"unit": None, "timestamps": ts, "data": vals}
    t_end = float(rows[-1][time_col]) if rows else 0
    return {"lap_number": 0, "lap_time_ms": int(t_end * 1000), "channels": channels,
            "gps_track": [], "sample_rate_hz": None, "metadata": {}}


# ── JSON ────────────────────────────────────────────────────────────────────

def _parse_json(file_path: str) -> list[dict[str, Any]]:
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return [{
        "lap_number": data.get("lap_number", 0),
        "lap_time_ms": data.get("lap_time_ms"),
        "channels": data.get("channels", {}),
        "gps_track": data.get("gps_track", []),
        "sample_rate_hz": data.get("sample_rate_hz"),
        "metadata": {},
    }]


# ── Stubs ────────────────────────────────────────────────────────────────────

def _parse_motec_ld(_: str) -> list[dict]:
    raise NotImplementedError("MoTeC .ld parsing not yet implemented")


def _parse_aim_drk(_: str) -> list[dict]:
    raise NotImplementedError("AiM .drk/.xdrk parsing not yet implemented")
