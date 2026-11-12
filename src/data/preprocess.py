"""Telemetry preprocessing and flight-level calculations."""

import pandas as pd


def calculate_power(voltage: pd.Series, current: pd.Series) -> pd.Series:
    """Calculate battery power in watts, clipping negative current."""
    voltage_values = pd.to_numeric(voltage, errors="coerce")
    current_values = pd.to_numeric(current, errors="coerce").clip(lower=0)
    return voltage_values * current_values


def calculate_energy_wh(time_s: pd.Series, power_w: pd.Series) -> float:
    """Integrate power over elapsed seconds using the trapezoidal rule."""
    samples = pd.DataFrame({"time_s": time_s, "power_w": power_w}).dropna()
    samples = samples.sort_values("time_s")
    if len(samples) < 2:
        return 0.0
    duration_s = samples["time_s"].diff().iloc[1:]
    average_power_w = (
        samples["power_w"].iloc[1:].to_numpy() + samples["power_w"].iloc[:-1].to_numpy()
    ) / 2
    return float((average_power_w * duration_s.to_numpy()).sum() / 3600)
