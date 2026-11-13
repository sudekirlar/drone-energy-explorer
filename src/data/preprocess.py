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
    distance_m = float("nan")
    if {"velocity_x", "velocity_y"}.issubset(telemetry.columns):
        ground_speed = calculate_ground_speed(telemetry["velocity_x"], telemetry["velocity_y"])
        distance_m = calculate_distance_m(telemetry["time"], ground_speed)
    return {
        "duration_s": duration_s,
        "energy_wh": energy_wh,
        "mean_power_w": mean_power_w,
        "distance_m": distance_m,
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
            "distance_m",
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


def calculate_distance_m(time_s: pd.Series, ground_speed_mps: pd.Series) -> float:
    """Integrate horizontal ground speed over time to obtain distance in meters."""
    samples = pd.DataFrame({"time_s": time_s, "speed_mps": ground_speed_mps}).dropna()
    samples = samples.sort_values("time_s")
    if len(samples) < 2:
        return 0.0
    dt = samples["time_s"].diff().iloc[1:].to_numpy()
    speeds = samples["speed_mps"].to_numpy()
    return float(((speeds[1:] + speeds[:-1]) / 2 * dt).sum())


def summarize_data_quality(telemetry: pd.DataFrame) -> dict:
    """Summarize basic telemetry quality without modifying the input."""
    time_s = pd.to_numeric(telemetry["time"], errors="coerce")
    current_a = pd.to_numeric(telemetry["battery_current"], errors="coerce")
    return {
        "row_count": len(telemetry),
        "missing_value_count": int(telemetry.isna().sum().sum()),
        "duplicate_row_count": int(telemetry.duplicated().sum()),
        "invalid_time_count": int(time_s.isna().sum()),
        "negative_time_count": int((time_s < 0).sum()),
        "negative_current_count": int((current_a < 0).sum()),
    }


def summarize_flight_quality(telemetry: pd.DataFrame) -> pd.DataFrame:
    """Summarize telemetry quality separately for each flight."""
    rows = []
    for flight, group in telemetry.groupby("flight", sort=True):
        rows.append({"flight": flight, **summarize_data_quality(group)})
    return pd.DataFrame(
        rows,
        columns=[
            "flight",
            "row_count",
            "missing_value_count",
            "duplicate_row_count",
            "invalid_time_count",
            "negative_time_count",
            "negative_current_count",
        ],
    )


def clean_telemetry(telemetry: pd.DataFrame, home_lat: float, home_lon: float) -> pd.DataFrame:
    """Clean one flight at its original sampling rate, without changing input."""
    import numpy as np

    required = {
        "flight",
        "time",
        "position_x",
        "position_y",
        "position_z",
        "velocity_x",
        "velocity_y",
        "velocity_z",
        "wind_speed",
        "battery_voltage",
        "battery_current",
    }
    missing = required - set(telemetry.columns)
    if missing:
        raise ValueError(f"Missing raw telemetry columns: {sorted(missing)}")
    if telemetry.empty:
        raise ValueError("Cannot clean an empty flight")
    if telemetry["flight"].nunique(dropna=False) != 1:
        raise ValueError("clean_telemetry expects exactly one flight")

    source = telemetry.copy()
    source["time"] = pd.to_numeric(source["time"], errors="coerce")
    if source["time"].isna().any():
        raise ValueError("Flight contains invalid timestamps")
    source = source.sort_values("time", kind="stable").reset_index(drop=True)
    t = source["time"].to_numpy(dtype=float)
    if not np.isfinite(t).all() or np.any(np.diff(t) <= 0):
        raise ValueError("Flight timestamps must be finite and strictly increasing")
    t = t - t[0]

    lat = pd.to_numeric(source["position_y"], errors="coerce").to_numpy(dtype=float)
    lon = pd.to_numeric(source["position_x"], errors="coerce").to_numpy(dtype=float)
    voltage = pd.to_numeric(source["battery_voltage"], errors="coerce").to_numpy(dtype=float)
    current = (
        pd.to_numeric(source["battery_current"], errors="coerce")
        .clip(lower=0)
        .to_numpy(dtype=float)
    )
    power = voltage * current
    energy = np.zeros(len(source), dtype=float)
    if len(source) > 1:
        energy[1:] = np.cumsum((power[1:] + power[:-1]) / 2 * np.diff(t) / 3600)

    radius_m = 6_371_000.0
    east = np.radians(lon - home_lon) * radius_m * np.cos(np.radians(home_lat))
    north = np.radians(lat - home_lat) * radius_m
    course = (
        np.degrees(
            np.arctan2(
                np.diff(east, prepend=east[0]),
                np.diff(north, prepend=north[0]),
            )
        )
        + 360
    ) % 360

    return pd.DataFrame(
        {
            "flight": int(source["flight"].iloc[0]),
            "t_s": t,
            "lat_deg": lat,
            "lon_deg": lon,
            "east_m": east,
            "north_m": north,
            "alt_rel_m": calculate_relative_altitude(source["position_z"]).to_numpy(dtype=float),
            "ground_speed_mps": calculate_ground_speed(
                source["velocity_x"], source["velocity_y"]
            ).to_numpy(dtype=float),
            "vertical_speed_mps": pd.to_numeric(source["velocity_z"], errors="coerce").to_numpy(
                dtype=float
            ),
            "course_deg": course,
            "airspeed_mps": pd.to_numeric(source["wind_speed"], errors="coerce").to_numpy(
                dtype=float
            ),
            "voltage_v": voltage,
            "current_a": current,
            "power_w": power,
            "energy_wh": energy,
        }
    )
