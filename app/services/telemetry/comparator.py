"""
Lap comparison engine.
Aligns telemetry channels by distance and computes time deltas.
"""
from __future__ import annotations

import numpy as np
from app.models.lap import Lap
from app.schemas.telemetry import CompareResult, TelemetryData, TelemetryChannel, LapDelta
from app.services.telemetry.parser import parse

# Number of points in the common distance axis
_DIST_POINTS = 500


def speed_to_distance_m(timestamps: list[float], speed_kmh: list[float]) -> list[float]:
    """Integrate speed (km/h) over time (s) → cumulative distance in metres."""
    dist = [0.0]
    for i in range(1, len(timestamps)):
        dt = timestamps[i] - timestamps[i - 1]
        v_avg = (speed_kmh[i] + speed_kmh[i - 1]) / 2
        dist.append(dist[-1] + v_avg * dt / 3.6)
    return dist


def _get_distance_and_time(data: dict) -> tuple[list[float], list[float]]:
    """Return (distance_m, time_s) for a parsed lap dict."""
    speed_ch = data["channels"].get("speed_gps") or data["channels"].get("speed_obd")
    if speed_ch and speed_ch.get("data") and speed_ch.get("timestamps"):
        ts = speed_ch["timestamps"]
        dist = speed_to_distance_m(ts, speed_ch["data"])
        return dist, ts
    # Fallback: no speed channel — use time as a proxy for distance
    ts = next((ch["timestamps"] for ch in data["channels"].values() if ch.get("timestamps")), [0.0])
    return ts, ts


def compare_laps(laps: list[Lap], channels: list[str] | None = None) -> CompareResult:
    parsed = []
    for lap in laps:
        if not lap.telemetry_file_path or not lap.telemetry_format:
            raise ValueError(f"Lap {lap.id} has no telemetry data uploaded")
        all_lap_data = parse(lap.telemetry_file_path, lap.telemetry_format)
        lap_data = next((d for d in all_lap_data if d["lap_number"] == lap.lap_number), None)
        if lap_data is None and all_lap_data:
            lap_data = all_lap_data[0]
        if lap_data is None:
            raise ValueError(f"Lap {lap.id} not found in telemetry file")
        parsed.append(lap_data)

    # Determine common channels
    channel_sets = [set(p["channels"].keys()) for p in parsed]
    common_channels = channel_sets[0].intersection(*channel_sets[1:])
    if channels:
        common_channels = common_channels & set(channels)

    # Compute per-lap distance and time arrays
    lap_distances: list[list[float]] = []
    lap_times: list[list[float]] = []
    for data in parsed:
        dist, ts = _get_distance_and_time(data)
        lap_distances.append(dist)
        lap_times.append(ts)

    # Common distance axis: 0 → min(each lap's total distance)
    max_common = min(d[-1] for d in lap_distances if d)
    common_dist = list(np.linspace(0.0, max_common, _DIST_POINTS))

    # Resample each channel onto the common distance axis
    telemetry_out: list[TelemetryData] = []
    for i, (lap, data) in enumerate(zip(laps, parsed)):
        lap_dist = lap_distances[i]
        ch_list = []
        for ch_name in common_channels:
            ch = data["channels"][ch_name]
            resampled = _resample(lap_dist, ch["data"], common_dist)
            ch_list.append(TelemetryChannel(
                name=ch_name,
                unit=ch.get("unit"),
                data=resampled,
                timestamps=common_dist,  # x-axis is distance (m)
            ))
        telemetry_out.append(TelemetryData(
            lap_id=lap.id,
            lap_time_ms=lap.lap_time_ms,
            sample_rate_hz=data.get("sample_rate_hz"),
            channels=ch_list,
            distance_m=common_dist,
        ))

    # Delta-T at each distance point:
    # For each lap, interpolate time_at_distance from (distance, time) pairs.
    # delta = time_lap(d) - time_ref(d)  →  positive means comparison is slower.
    deltas: list[LapDelta] = []
    ref_dist = np.array(lap_distances[0])
    ref_time = np.array(lap_times[0])
    ref_t_at_d = np.interp(common_dist, ref_dist, ref_time)

    for i, (lap, data) in enumerate(zip(laps[1:], parsed[1:]), start=1):
        cmp_dist = np.array(lap_distances[i])
        cmp_time = np.array(lap_times[i])
        cmp_t_at_d = np.interp(common_dist, cmp_dist, cmp_time)
        delta = (cmp_t_at_d - ref_t_at_d).tolist()
        deltas.append(LapDelta(
            reference_lap_id=laps[0].id,
            comparison_lap_id=lap.id,
            timestamps=common_dist,  # x-axis is distance (m)
            delta_seconds=delta,
        ))

    return CompareResult(
        laps=telemetry_out,
        deltas=deltas,
        channels_available=sorted(common_channels),
    )


def _resample(src_d: list[float], src_v: list[float], target_d: list[float]) -> list[float]:
    if not src_d or not src_v:
        return [0.0] * len(target_d)
    return list(np.interp(target_d, src_d, src_v))
