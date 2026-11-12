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
