"""Build processed drone telemetry tables from the CMU dataset."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.preprocess import (
    calculate_energy_wh,
    calculate_ground_speed,
    calculate_relative_altitude,
    summarize_time_gaps,
)

RAW = Path("data/raw")
OUTPUT = Path("data/intermediate")
ROUTES = {f"R{i}" for i in range(1, 8)}
EARTH_RADIUS_M = 6_371_000.0


def gps_distance_m(lat: np.ndarray, lon: np.ndarray) -> float:
    """Sum great-circle distances between successive GPS samples."""
    lat_rad = np.radians(lat)
    lon_rad = np.radians(lon)
    dlat = np.diff(lat_rad)
    dlon = np.diff(lon_rad)
    a = np.sin(dlat / 2) ** 2 + np.cos(lat_rad[:-1]) * np.cos(lat_rad[1:]) * np.sin(dlon / 2) ** 2
    return float(np.sum(2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(np.clip(a, 0, 1)))))


def build() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    raw = pd.read_csv(RAW / "flights.csv")
    params = pd.read_csv(RAW / "parameters.csv")

    raw = raw.loc[raw["route"].isin(ROUTES)].copy()
    params = params.loc[params["route"].isin(ROUTES)].copy()

    home = raw.loc[raw["route"] == "R1"].iloc[0]
    home_lat = float(home["position_y"])
    home_lon = float(home["position_x"])

    flight_rows = []
    telemetry_rows = []

    for flight_id, group in raw.groupby("flight", sort=True):
        group = group.sort_values("time").copy()
        param = params.loc[params["flight"] == flight_id].iloc[0]

        t = group["time"].to_numpy(dtype=float)
        t = t - t[0]

        lat = group["position_y"].to_numpy(dtype=float)
        lon = group["position_x"].to_numpy(dtype=float)
        voltage = group["battery_voltage"].to_numpy(dtype=float)
        current = np.maximum(group["battery_current"].to_numpy(dtype=float), 0)
        power = voltage * current

        energy = np.zeros(len(group), dtype=float)
        energy[1:] = np.cumsum((power[1:] + power[:-1]) / 2 * np.diff(t) / 3600)

        ground_speed = calculate_ground_speed(group["velocity_x"], group["velocity_y"]).to_numpy(
            dtype=float
        )

        alt_rel = calculate_relative_altitude(group["position_z"]).to_numpy(dtype=float)

        east = np.radians(lon - home_lon) * EARTH_RADIUS_M * np.cos(np.radians(home_lat))
        north = np.radians(lat - home_lat) * EARTH_RADIUS_M

        distance = gps_distance_m(lat, lon)
        duration = float(t[-1] - t[0])
        total_energy = calculate_energy_wh(
            group["time"].reset_index(drop=True),
            pd.Series(power),
        )
        gaps = summarize_time_gaps(group["time"])

        target_alt = pd.to_numeric(pd.Series([param["altitude"]]), errors="coerce").iloc[0]

        start_time = pd.to_datetime(f"{param['date']} {param['local_time']}", errors="coerce")

        flight_rows.append(
            {
                "flight": int(flight_id),
                "route": str(param["route"]),
                "payload_g": int(param["payload"]),
                "speed_mps": int(param["speed"]),
                "altitude_m": float(target_alt),
                "variable_altitude": bool(pd.isna(target_alt)),
                "start_time": start_time,
                "local_time_raw": str(param["local_time"]),
                "time_corrected": False,
                "in_design": bool(
                    param["route"] == "R1"
                    and param["payload"] in (0, 250, 500)
                    and int(flight_id) != 76
                ),
                "is_outlier": False,
                "outlier_reason": None,
                "duration_s": duration,
                "distance_m": distance,
                "energy_wh": total_energy,
                "wh_per_km": total_energy * 1000 / distance if distance > 0 else np.nan,
                "mean_power_w": total_energy * 3600 / duration if duration > 0 else 0.0,
                "start_voltage_v": float(voltage[0]),
                "end_voltage_v": float(voltage[-1]),
                "voltage_drop_v": float(voltage[0] - voltage[-1]),
                "mean_airspeed_mps": float(group["wind_speed"].mean()),
                "sample_count": len(group),
                **gaps,
                "cruise_power_w": np.nan,
                "climb_power_w": np.nan,
                "wp_turn_count": pd.NA,
            }
        )

        samples = pd.DataFrame(
            {
                "flight": int(flight_id),
                "t_s": t,
                "lat_deg": lat,
                "lon_deg": lon,
                "east_m": east,
                "north_m": north,
                "alt_rel_m": alt_rel,
                "ground_speed_mps": ground_speed,
                "vertical_speed_mps": group["velocity_z"].to_numpy(dtype=float),
                "course_deg": (
                    np.degrees(
                        np.arctan2(
                            group["velocity_x"].to_numpy(dtype=float),
                            group["velocity_y"].to_numpy(dtype=float),
                        )
                    )
                    + 360
                )
                % 360,
                "airspeed_mps": group["wind_speed"].to_numpy(dtype=float),
                "voltage_v": voltage,
                "current_a": current,
                "power_w": power,
                "energy_wh": energy,
            }
        )

        # Keep the last available sample in each one-second interval.
        samples["t_s"] = np.floor(samples["t_s"]).astype(int)
        samples = samples.groupby("t_s", as_index=False).last()
        samples["t_s"] = samples["t_s"].astype(float)

        # Platform-owned fields will be supplied by the phase pipeline.
        samples["t_since_takeoff_s"] = np.nan
        samples["phase"] = None
        samples["sub_phase"] = None

        telemetry_rows.append(samples)

    flights = pd.DataFrame(flight_rows)
    telemetry = pd.concat(telemetry_rows, ignore_index=True)

    flights.to_parquet(OUTPUT / "flights_data.parquet", index=False)
    telemetry.to_parquet(OUTPUT / "telemetry_data_1hz.parquet", index=False)

    quality_log = [
        {
            "rule_id": "route-filter",
            "description": "Exclude ground and hover test routes.",
            "rows_affected": int(
                pd.read_csv(RAW / "flights.csv", usecols=["route"])["route"]
                .isin(ROUTES)
                .eq(False)
                .sum()
            ),
            "flights_affected": int(209 - len(flights)),
            "iso25012": "Consistency",
        },
        {
            "rule_id": "negative-current",
            "description": "Clip negative battery current readings to zero.",
            "rows_affected": int((raw["battery_current"] < 0).sum()),
            "flights_affected": int(raw.loc[raw["battery_current"] < 0, "flight"].nunique()),
            "iso25012": "Accuracy",
        },
    ]

    (OUTPUT / "quality_log.json").write_text(json.dumps(quality_log, indent=2), encoding="utf-8")

    print(f"Flights: {len(flights)}")
    print(f"Telemetry rows (1 Hz): {len(telemetry)}")
    print(f"Quality rules: {len(quality_log)}")
    print(f"Files written to: {OUTPUT}")


if __name__ == "__main__":
    build()
