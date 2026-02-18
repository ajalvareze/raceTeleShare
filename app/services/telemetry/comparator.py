"""
Lap comparison engine.
Aligns telemetry channels by distance or time and computes deltas.
"""
from __future__ import annotations

import numpy as np
from app.models.lap import Lap
from app.schemas.telemetry import CompareResult, TelemetryData, TelemetryChannel, LapDelta
from app.services.telemetry.parser import parse


def compare_laps(laps: list[Lap], channels: list[str] | None = None) -> CompareResult:
    parsed = []
    for lap in laps:
        if not lap.telemetry_file_path or not lap.telemetry_format:
            raise ValueError(f"Lap {lap.id} has no telemetry data uploaded")
        parsed.append(parse(lap.telemetry_file_path, lap.telemetry_format))

    # Determine common channels
    channel_sets = [set(p["channels"].keys()) for p in parsed]
    common_channels = channel_sets[0].intersection(*channel_sets[1:])
    if channels:
        common_channels = common_channels & set(channels)

    reference = parsed[0]
    ref_timestamps = _get_time_axis(reference)

    telemetry_out: list[TelemetryData] = []
    for i, (lap, data) in enumerate(zip(laps, parsed)):
        ch_list = []
        for ch_name in common_channels:
            ch = data["channels"][ch_name]
            # Resample to reference time axis
            resampled = _resample(ch["timestamps"], ch["data"], ref_timestamps)
            ch_list.append(
                TelemetryChannel(
                    name=ch_name,
                    unit=ch.get("unit"),
                    data=resampled,
                    timestamps=ref_timestamps,
                )
            )
        telemetry_out.append(
            TelemetryData(
                lap_id=lap.id,
                lap_time_ms=lap.lap_time_ms,
                sample_rate_hz=data.get("sample_rate_hz"),
                channels=ch_list,
            )
        )

    # Compute time deltas (cumulative time gained/lost vs reference)
    deltas: list[LapDelta] = []
    for i, (lap, data) in enumerate(zip(laps[1:], parsed[1:]), start=1):
        comp_timestamps = _get_time_axis(data)
        delta = _compute_delta(ref_timestamps, comp_timestamps)
        deltas.append(
            LapDelta(
                reference_lap_id=laps[0].id,
                comparison_lap_id=lap.id,
                timestamps=ref_timestamps,
                delta_seconds=delta,
            )
        )

    return CompareResult(
        laps=telemetry_out,
        deltas=deltas,
        channels_available=sorted(common_channels),
    )


def _get_time_axis(data: dict) -> list[float]:
    for ch in data["channels"].values():
        if ch["timestamps"]:
            return ch["timestamps"]
    return []


def _resample(src_t: list[float], src_v: list[float], target_t: list[float]) -> list[float]:
    if not src_t or not src_v:
        return [0.0] * len(target_t)
    return list(np.interp(target_t, src_t, src_v))


def _compute_delta(ref_t: list[float], cmp_t: list[float]) -> list[float]:
    """
    Returns cumulative time delta at each point of the reference axis.
    Positive = comparison lap is slower at that point.
    """
    if not ref_t or not cmp_t:
        return []
    ref_arr = np.array(ref_t)
    cmp_arr = np.array(cmp_t)
    # Normalise both to [0,1] distance fraction, then compute time difference
    ref_norm = ref_arr / ref_arr[-1] if ref_arr[-1] else ref_arr
    cmp_norm = cmp_arr / cmp_arr[-1] if cmp_arr[-1] else cmp_arr
    # time at each fraction for comparison lap
    cmp_time_at_ref = np.interp(ref_norm, cmp_norm, cmp_arr)
    delta = cmp_time_at_ref - ref_arr
    return delta.tolist()
