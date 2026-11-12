"""Synthetic placeholder data generator for Drone Delivery Energy Explorer."""

import numpy as np
import pandas as pd


def make_demo_data(n_flights: int = 120, seed: int = 42) -> pd.DataFrame:
    """Generate realistic synthetic flight-level data matching the T0/T1 contract."""
    rng = np.random.default_rng(seed)

    payloads = rng.choice([0, 250, 500, 750], size=n_flights)
    altitudes = rng.choice([25, 50, 75, 100], size=n_flights)
    speeds = rng.choice([4, 6, 8, 10, 12], size=n_flights)
    routes = rng.choice(
        ["R1", "R2", "R3", "R4", "R5", "R6", "R7"],
        size=n_flights,
        p=[0.4, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
    )
    phases = rng.choice(
        ["Takeoff", "Climb", "Cruise", "Descent", "Landing"],
        size=n_flights,
        p=[0.1, 0.15, 0.5, 0.15, 0.1],
    )
    flagged = rng.choice([False, True], size=n_flights, p=[0.9, 0.1])

    wind_speed = np.round(rng.uniform(0.5, 8.5, size=n_flights), 2)
    duration_s = np.round(rng.uniform(180, 900, size=n_flights), 1)
    distance_m = np.round(speeds * duration_s * rng.uniform(0.85, 1.05, size=n_flights), 1)

    base_power = 180 + 0.08 * payloads + 1.8 * (speeds**1.6) + 0.25 * altitudes + 3.5 * wind_speed
    power_w = np.round(base_power + rng.normal(0, 12, size=n_flights), 2)
    energy_wh = np.round((power_w * duration_s) / 3600.0, 2)
    energy_per_km = np.round(energy_wh / np.maximum(distance_m / 1000.0, 0.1), 2)

    df = pd.DataFrame(
        {
            "flight": [f"F{i:03d}" for i in range(1, n_flights + 1)],
            "payload_g": payloads,
            "target_altitude": altitudes,
            "target_speed": speeds,
            "route": routes,
            "estimated_phase": phases,
            "flagged": flagged,
            "wind_speed": wind_speed,
            "duration_s": duration_s,
            "distance_m": distance_m,
            "mean_power_w": power_w,
            "total_energy_wh": energy_wh,
            "energy_per_km_wh": energy_per_km,
            "is_synthetic": True,
        }
    )
    return df
