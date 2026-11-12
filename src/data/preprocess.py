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


def summarize_flight(telemetry: pd.DataFrame) -> dict:
    """Summarize energy and duration for one flight."""
    if telemetry.empty:
        raise ValueError("Cannot summarize an empty flight")
    power_w = calculate_power(telemetry["battery_voltage"], telemetry["battery_current"])
    duration_s = float(telemetry["time"].max() - telemetry["time"].min())
    energy_wh = calculate_energy_wh(telemetry["time"], power_w)
    mean_power_w = energy_wh * 3600 / duration_s if duration_s > 0 else 0.0
    gap_summary = summarize_time_gaps(telemetry["time"])
    return {
        "duration_s": duration_s,
        "energy_wh": energy_wh,
        "mean_power_w": mean_power_w,
        "sample_count": len(telemetry),
        **gap_summary,
    }


def summarize_flights(telemetry: pd.DataFrame) -> pd.DataFrame:
    """Summarize energy and duration for every route-flight pair."""
    rows = []
    for (flight, route), group in telemetry.groupby(["flight", "route"], sort=True):
        summary = summarize_flight(group)
        rows.append({"flight": flight, "route": route, **summary})
    return pd.DataFrame(
        rows,
        columns=[
            "flight",
            "route",
            "duration_s",
            "energy_wh",
            "mean_power_w",
            "sample_count",
            "max_gap_s",
            "large_gap_count",
        ],
    )


def parse_target_altitude(altitude: pd.Series) -> pd.Series:
    """Convert single altitudes to numbers; mark multi-level profiles as missing."""
    return pd.to_numeric(altitude, errors="coerce")


def summarize_time_gaps(time_s: pd.Series, threshold_s: float = 1.0) -> dict:
    """Summarize sampling gaps for one flight."""
    times = pd.to_numeric(time_s, errors="coerce").dropna().sort_values()
    gaps = times.diff().dropna()
    return {
        "max_gap_s": float(gaps.max()) if not gaps.empty else 0.0,
        "large_gap_count": int((gaps > threshold_s).sum()),
    }


def calculate_relative_altitude(position_z: pd.Series) -> pd.Series:
    """Calculate altitude relative to the first valid position sample."""
    altitude = pd.to_numeric(position_z, errors="coerce")
    first_valid = altitude.first_valid_index()
    if first_valid is None:
        return altitude
    return altitude - altitude.loc[first_valid]


def calculate_ground_speed(velocity_x: pd.Series, velocity_y: pd.Series) -> pd.Series:
    """Calculate horizontal ground-speed magnitude in meters per second."""
    vx = pd.to_numeric(velocity_x, errors="coerce")
    vy = pd.to_numeric(velocity_y, errors="coerce")
    return (vx**2 + vy**2) ** 0.5
