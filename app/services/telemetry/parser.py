"""
Telemetry file parsers.

Each parser reads a file and returns a dict of:
    {
        "channels": {
            "channel_name": {
                "unit": str | None,
                "timestamps": list[float],   # seconds from lap start
                "data": list[float],
            }
        },
        "sample_rate_hz": float | None,
        "lap_time_ms": int | None,
    }

Supported formats:
  - csv   : generic CSV (first column = timestamp in seconds)
  - json  : {"channels": {...}} structure matching the dict above
  - ld    : MoTeC .ld (stub — requires motec library or custom binary parser)
  - drk   : AiM .drk  (stub)
"""
from __future__ import annotations

import json
import csv
import io
from typing import Any


def parse(file_path: str, fmt: str) -> dict[str, Any]:
    parsers = {
        "csv": _parse_csv,
        "json": _parse_json,
        "ld": _parse_motec_ld,
        "drk": _parse_aim_drk,
        "xdrk": _parse_aim_drk,
    }
    parser = parsers.get(fmt.lower())
    if not parser:
        raise ValueError(f"No parser available for format: {fmt}")
    return parser(file_path)


def _parse_csv(file_path: str) -> dict[str, Any]:
    channels: dict[str, dict] = {}
    with open(file_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        time_col = headers[0] if headers else "time"

        for col in headers[1:]:
            channels[col] = {"unit": None, "timestamps": [], "data": []}

        for row in reader:
            try:
                t = float(row[time_col])
            except (KeyError, ValueError):
                continue
            for col in headers[1:]:
                try:
                    channels[col]["timestamps"].append(t)
                    channels[col]["data"].append(float(row[col]))
                except (KeyError, ValueError):
                    pass

    lap_time_ms = None
    for ch in channels.values():
        if ch["timestamps"]:
            lap_time_ms = int(ch["timestamps"][-1] * 1000)
            break

    return {"channels": channels, "sample_rate_hz": None, "lap_time_ms": lap_time_ms}


def _parse_json(file_path: str) -> dict[str, Any]:
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)
    return {
        "channels": data.get("channels", {}),
        "sample_rate_hz": data.get("sample_rate_hz"),
        "lap_time_ms": data.get("lap_time_ms"),
    }


def _parse_motec_ld(_file_path: str) -> dict[str, Any]:
    # Stub: integrate a MoTeC .ld parser here (e.g. motec python library)
    raise NotImplementedError("MoTeC .ld parsing not yet implemented")


def _parse_aim_drk(_file_path: str) -> dict[str, Any]:
    # Stub: integrate AiM .drk / .xdrk parser here
    raise NotImplementedError("AiM .drk/.xdrk parsing not yet implemented")
