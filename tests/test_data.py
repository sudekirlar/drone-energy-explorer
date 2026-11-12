"""Tests for telemetry preprocessing."""

import pandas as pd

from src.data.preprocess import calculate_power


def test_calculate_power_clips_negative_current():
    """Power must be non-negative when current is negative."""
    voltage = pd.Series([24, 24, 20])
    current = pd.Series([5, -2, 3])
    result = calculate_power(voltage, current)
    assert result.tolist() == [120, 0, 60]
