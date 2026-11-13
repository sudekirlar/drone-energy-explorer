"""Raw-rate telemetry cleaning contract and energy conservation tests."""

import pandas as pd
import pytest

from src.data.preprocess import calculate_energy_wh, clean_telemetry


def example_flight():
    return pd.DataFrame(
        {
            "flight": [1, 1, 1],
            "time": [0.0, 0.2, 0.5],
            "position_x": [10.0, 10.00001, 10.00002],
            "position_y": [40.0, 40.0, 40.0],
            "position_z": [100.0, 101.0, 102.0],
            "velocity_x": [1.0, 1.0, 1.0],
            "velocity_y": [0.0, 0.0, 0.0],
            "velocity_z": [0.0, 0.0, 0.0],
            "wind_speed": [2.0, 2.0, 2.0],
            "battery_voltage": [20.0, 20.0, 20.0],
            "battery_current": [5.0, -2.0, 5.0],
        }
    )


def test_clean_telemetry_preserves_raw_rate_and_input():
    raw = example_flight()
    original = raw.copy(deep=True)
    result = clean_telemetry(raw, 40.0, 10.0)
    pd.testing.assert_frame_equal(raw, original)
    assert result["t_s"].tolist() == pytest.approx([0.0, 0.2, 0.5])
    assert result["current_a"].tolist() == pytest.approx([5.0, 0.0, 5.0])
    assert result["power_w"].tolist() == pytest.approx([100.0, 0.0, 100.0])
    assert result["energy_wh"].iloc[-1] == pytest.approx(25 / 3600)
    assert result["course_deg"].iloc[1] == pytest.approx(90.0, abs=0.1)


def test_clean_telemetry_energy_matches_raw_integral():
    raw = example_flight()
    result = clean_telemetry(raw, 40.0, 10.0)
    expected = calculate_energy_wh(raw["time"], result["power_w"])
    assert result["energy_wh"].iloc[-1] == pytest.approx(expected)


def test_clean_telemetry_rejects_mixed_flights():
    raw = example_flight()
    raw.loc[2, "flight"] = 2
    with pytest.raises(ValueError, match="exactly one flight"):
        clean_telemetry(raw, 40.0, 10.0)


def test_clean_telemetry_rejects_duplicate_timestamps():
    raw = example_flight()
    raw.loc[2, "time"] = 0.2
    with pytest.raises(ValueError, match="strictly increasing"):
        clean_telemetry(raw, 40.0, 10.0)
