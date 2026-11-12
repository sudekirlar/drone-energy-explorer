"""Telemetry preprocessing and flight-level calculations."""

import pandas as pd


def calculate_power(voltage: pd.Series, current: pd.Series) -> pd.Series:
    """Calculate battery power in watts, clipping negative current."""
    voltage_values = pd.to_numeric(voltage, errors="coerce")
    current_values = pd.to_numeric(current, errors="coerce").clip(lower=0)
    return voltage_values * current_values
