"""Tests for telemetry preprocessing."""

import pandas as pd

from src.data.preprocess import calculate_energy_wh, calculate_power


def test_calculate_power_clips_negative_current():
    """Power must be non-negative when current is negative."""
    voltage = pd.Series([24, 24, 20])
    current = pd.Series([5, -2, 3])
    result = calculate_power(voltage, current)
    assert result.tolist() == [120, 0, 60]


def test_calculate_energy_constant_power():
    """Constant power over 30 seconds should produce 1 Wh."""
    result = calculate_energy_wh(pd.Series([0, 10, 30]), pd.Series([120, 120, 120]))
    assert abs(result - 1.0) < 1e-9


def test_calculate_energy_variable_power():
    """Use actual time intervals when integrating variable power."""
    result = calculate_energy_wh(pd.Series([0, 10, 30]), pd.Series([60, 120, 180]))
    assert abs(result - (3900 / 3600)) < 1e-9


def test_summarize_flight():
    """Summarize duration, energy, mean power, and sample count."""
    from src.data.preprocess import summarize_flight

    telemetry = pd.DataFrame(
        {"time": [0, 10, 30], "battery_voltage": [12, 12, 12], "battery_current": [10, 10, 10]}
    )
    result = summarize_flight(telemetry)
    assert result["duration_s"] == 30.0
    assert abs(result["energy_wh"] - 1.0) < 1e-9
    assert abs(result["mean_power_w"] - 120.0) < 1e-9
    assert result["sample_count"] == 3


def test_summarize_flight_rejects_empty_data():
    """Reject an empty flight instead of reporting zero energy."""
    import pytest

    from src.data.preprocess import summarize_flight

    with pytest.raises(ValueError, match="empty flight"):
        summarize_flight(pd.DataFrame())


def test_summarize_flights_groups_separately():
    """Summarize each flight independently."""
    from src.data.preprocess import summarize_flights

    telemetry = pd.DataFrame(
        {
            "flight": [1, 1, 2, 2],
            "route": ["R1", "R1", "R2", "R2"],
            "time": [0, 30, 0, 30],
            "battery_voltage": [12, 12, 12, 12],
            "battery_current": [10, 10, 20, 20],
        }
    )
    result = summarize_flights(telemetry).set_index("flight")
    assert len(result) == 2
    assert abs(result.loc[1, "energy_wh"] - 1.0) < 1e-9
    assert abs(result.loc[2, "energy_wh"] - 2.0) < 1e-9
    assert result["sample_count"].tolist() == [2, 2]


def test_parse_target_altitude_preserves_multi_level_profiles():
    """Convert numeric targets while keeping multi-level profiles missing."""
    from src.data.preprocess import parse_target_altitude

    altitude = pd.Series(["25", "50", "100", "25-50-100-25"])
    result = parse_target_altitude(altitude)
    assert result.iloc[:3].tolist() == [25.0, 50.0, 100.0]
    assert pd.isna(result.iloc[3])
    assert altitude.iloc[3] == "25-50-100-25"


def test_summarize_time_gaps():
    """Count gaps above the threshold and report the largest gap."""
    from src.data.preprocess import summarize_time_gaps

    result = summarize_time_gaps(pd.Series([0.0, 0.2, 0.4, 2.4, 2.6]))
    assert abs(result["max_gap_s"] - 2.0) < 1e-9
    assert result["large_gap_count"] == 1
    assert summarize_time_gaps(pd.Series([0.0])) == {"max_gap_s": 0.0, "large_gap_count": 0}


def test_flight_summary_includes_time_gap_quality():
    """Include sampling-gap quality metrics in flight summaries."""
    from src.data.preprocess import summarize_flights

    telemetry = pd.DataFrame(
        {
            "flight": [1, 1, 1],
            "route": ["R1"] * 3,
            "time": [0.0, 0.2, 2.2],
            "battery_voltage": [12] * 3,
            "battery_current": [10] * 3,
        }
    )
    result = summarize_flights(telemetry).iloc[0]
    assert abs(result["max_gap_s"] - 2.0) < 1e-9
    assert result["large_gap_count"] == 1
    assert abs(result["energy_wh"] - (120 * 2.2 / 3600)) < 1e-9


def test_calculate_relative_altitude():
    """Calculate altitude relative to the first valid sample."""
    from src.data.preprocess import calculate_relative_altitude

    altitude = pd.Series([float("nan"), 270.0, 295.0, 268.0])
    result = calculate_relative_altitude(altitude)
    assert pd.isna(result.iloc[0])
    assert result.iloc[1:].tolist() == [0.0, 25.0, -2.0]


def test_calculate_ground_speed():
    """Calculate horizontal speed from velocity components."""
    from src.data.preprocess import calculate_ground_speed

    vx = pd.Series([3.0, 0.0, -3.0, float("nan")])
    vy = pd.Series([4.0, 0.0, 4.0, 2.0])
    result = calculate_ground_speed(vx, vy)
    assert result.iloc[:3].tolist() == [5.0, 0.0, 5.0]
    assert pd.isna(result.iloc[3])


def test_calculate_distance_m():
    """Integrate ground speed using actual time intervals."""
    from src.data.preprocess import calculate_distance_m

    time_s = pd.Series([0.0, 2.0, 5.0])
    speed_mps = pd.Series([2.0, 4.0, 4.0])
    assert calculate_distance_m(time_s, speed_mps) == 18.0
