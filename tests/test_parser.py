"""
Tests for the TrackAddict CSV telemetry parser.
"""
import pathlib
import pytest
from app.services.telemetry.parser import parse, _parse_trackaddict_meta

SAMPLE_CSV = str(pathlib.Path(__file__).parent.parent / "uploads" / "sample-session.csv")


@pytest.fixture(scope="module")
def parsed_laps():
    return parse(SAMPLE_CSV, "csv")


def test_parse_returns_list(parsed_laps):
    assert isinstance(parsed_laps, list)
    assert len(parsed_laps) > 0


def test_lap_count(parsed_laps):
    # Sample file has laps 0–12 (outlap + 11 timed + inlap)
    assert len(parsed_laps) == 13


def test_lap_numbers_sequential(parsed_laps):
    lap_nums = [l["lap_number"] for l in parsed_laps]
    assert lap_nums == list(range(13))


def test_outlap_inlap_flags(parsed_laps):
    assert parsed_laps[0]["is_outlap"] is True
    assert parsed_laps[0]["is_inlap"] is False
    assert parsed_laps[-1]["is_inlap"] is True
    assert parsed_laps[-1]["is_outlap"] is False
    # Middle laps are neither
    for lap in parsed_laps[1:-1]:
        assert not lap["is_outlap"]
        assert not lap["is_inlap"]


def test_required_channels_present(parsed_laps):
    # At least one timed lap should have the main channels
    timed = [l for l in parsed_laps if l.get("lap_time_ms") and not l["is_outlap"] and not l["is_inlap"]]
    assert timed, "No valid timed laps found"
    lap = timed[0]
    for ch in ("speed_gps", "throttle", "brake", "rpm"):
        assert ch in lap["channels"], f"Missing channel: {ch}"


def test_channel_data_lengths_match_timestamps(parsed_laps):
    for lap in parsed_laps:
        for name, ch in lap["channels"].items():
            assert len(ch["data"]) == len(ch["timestamps"]), \
                f"Lap {lap['lap_number']} channel {name}: data/timestamps length mismatch"


def test_lap_timestamps_start_at_zero(parsed_laps):
    for lap in parsed_laps:
        for ch in lap["channels"].values():
            if ch["timestamps"]:
                assert ch["timestamps"][0] == pytest.approx(0.0, abs=0.01), \
                    f"Lap {lap['lap_number']} timestamps don't start at 0"
                break


def test_gps_track_format(parsed_laps):
    # GPS track should be list of [time, lat, lon, alt]
    timed = [l for l in parsed_laps if l.get("gps_track") and len(l["gps_track"]) > 10]
    assert timed, "No laps with GPS data"
    point = timed[0]["gps_track"][0]
    assert len(point) == 4
    time_s, lat, lon, alt = point
    assert time_s == pytest.approx(0.0, abs=0.01)
    assert 4.0 < lat < 6.0,   "Latitude outside Colombia range"
    assert -75.0 < lon < -72.0, "Longitude outside Colombia range"


def test_best_lap_time(parsed_laps):
    timed = [l for l in parsed_laps if l.get("lap_time_ms") and not l["is_outlap"] and not l["is_inlap"]]
    best = min(timed, key=lambda l: l["lap_time_ms"])
    # Best lap is ~1:36.971 (96971 ms) ± 2 s
    assert abs(best["lap_time_ms"] - 96971) < 2000, \
        f"Unexpected best lap time: {best['lap_time_ms']} ms"


def test_metadata_vehicle(parsed_laps):
    meta = parsed_laps[0]["metadata"]
    assert meta.get("vehicle"), "Vehicle metadata missing"
    assert "Renault" in meta["vehicle"]


def test_unsupported_format_raises():
    with pytest.raises(ValueError, match="No parser available"):
        parse("/some/file.xyz", "xyz")


def test_parse_trackaddict_meta_lap_times():
    meta_lines = [
        "# Lap 1: 1:37.500\n",
        "# Lap 2: 1:36.971\n",
        "# Vehicle: Test Car\n",
    ]
    meta = _parse_trackaddict_meta(meta_lines)
    assert meta["lap_times"][1] == 97500
    assert meta["lap_times"][2] == 96971
    assert meta["vehicle"] == "Test Car"
