"""
Tests for the distance-based lap comparator.
"""
import pathlib
import pytest
from app.services.telemetry.comparator import speed_to_distance_m, compare_laps

SAMPLE_CSV = str(pathlib.Path(__file__).parent.parent / "uploads" / "sample-session.csv")


# ── Unit tests for distance computation ─────────────────────────────────────

def test_distance_zero_speed():
    ts = [0.0, 1.0, 2.0]
    speed = [0.0, 0.0, 0.0]
    dist = speed_to_distance_m(ts, speed)
    assert dist == [0.0, 0.0, 0.0]


def test_distance_constant_speed():
    # 36 km/h = 10 m/s → 10 m per second
    ts = [0.0, 1.0, 2.0, 3.0]
    speed = [36.0, 36.0, 36.0, 36.0]
    dist = speed_to_distance_m(ts, speed)
    assert dist[0] == pytest.approx(0.0)
    assert dist[1] == pytest.approx(10.0, rel=0.01)
    assert dist[2] == pytest.approx(20.0, rel=0.01)
    assert dist[3] == pytest.approx(30.0, rel=0.01)


def test_distance_always_increasing():
    ts = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
    speed = [50.0, 80.0, 120.0, 100.0, 60.0, 40.0]
    dist = speed_to_distance_m(ts, speed)
    for i in range(1, len(dist)):
        assert dist[i] >= dist[i - 1], f"Distance decreased at index {i}"


def test_distance_single_point():
    dist = speed_to_distance_m([0.0], [100.0])
    assert dist == [0.0]


def test_distance_result_length():
    ts = list(range(100))
    speed = [80.0] * 100
    dist = speed_to_distance_m(ts, speed)
    assert len(dist) == 100


# ── Integration tests using sample CSV ──────────────────────────────────────

class MockLap:
    """Minimal stand-in for a Lap ORM object."""
    def __init__(self, lap_id, lap_number, file_path, fmt, lap_time_ms=None):
        self.id = lap_id
        self.lap_number = lap_number
        self.telemetry_file_path = file_path
        self.telemetry_format = fmt
        self.lap_time_ms = lap_time_ms
        self.gps_track = None


@pytest.fixture(scope="module")
def two_timed_laps():
    """Return MockLap objects for laps 7 and 8 (both timed, valid)."""
    return [
        MockLap(7, 7, SAMPLE_CSV, "csv", 98000),
        MockLap(8, 8, SAMPLE_CSV, "csv", 96971),
    ]


def test_compare_returns_result(two_timed_laps):
    from app.schemas.telemetry import CompareResult
    result = compare_laps(two_timed_laps)
    assert isinstance(result, CompareResult)


def test_compare_distance_axis(two_timed_laps):
    result = compare_laps(two_timed_laps)
    for lap_data in result.laps:
        for ch in lap_data.channels:
            # x-axis should be distance in metres, starting at 0
            assert ch.timestamps[0] == pytest.approx(0.0, abs=1.0)
            assert ch.timestamps[-1] > 100, "Distance axis too short — expected hundreds of metres"


def test_compare_common_channels(two_timed_laps):
    result = compare_laps(two_timed_laps)
    assert "speed_gps" in result.channels_available
    assert "throttle" in result.channels_available
    assert "brake" in result.channels_available


def test_compare_channel_data_length_matches_axis(two_timed_laps):
    result = compare_laps(two_timed_laps)
    for lap_data in result.laps:
        for ch in lap_data.channels:
            assert len(ch.data) == len(ch.timestamps), \
                f"Channel {ch.name}: data/axis length mismatch"


def test_compare_delta_is_present(two_timed_laps):
    result = compare_laps(two_timed_laps)
    assert len(result.deltas) == 1
    delta = result.deltas[0]
    assert delta.reference_lap_id == 7
    assert delta.comparison_lap_id == 8
    assert len(delta.delta_seconds) == len(delta.timestamps)


def test_compare_delta_axis_is_distance(two_timed_laps):
    result = compare_laps(two_timed_laps)
    delta = result.deltas[0]
    assert delta.timestamps[0] == pytest.approx(0.0, abs=1.0)
    assert delta.timestamps[-1] > 100


def test_compare_missing_telemetry_raises():
    bad_lap = MockLap(99, 1, None, None)
    with pytest.raises(ValueError, match="no telemetry data"):
        compare_laps([bad_lap, bad_lap])
