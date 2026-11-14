"""Unit tests for src/charts/flight_heatmap.py."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from src.charts.flight_heatmap import (
    build_flight_time_heatmap,
    summarize_climb_band_by_altitude,
)


def _sample_heatmap_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    flights = pd.DataFrame(
        {
            "flight": [1, 2, 3, 4, 5],
            "route": ["R1", "R1", "R1", "R1", "R2"],
            "in_design": [True, True, True, True, False],
            "altitude_m": [25.0, 25.0, 100.0, 100.0, 50.0],
            "speed_mps": [4.0, 12.0, 4.0, 12.0, 8.0],
            "payload_g": [0, 500, 0, 500, 250],
            "energy_wh": [40.0, 65.0, 55.0, 90.0, 70.0],
            "wh_per_km": [25.0, 35.0, 30.0, 45.0, 33.0],
            "duration_s": [16.0, 16.0, 20.0, 20.0, 18.0],
            "cruise_power_w": [450.0, 520.0, 460.0, 530.0, 490.0],
            "climb_power_w": [560.0, 610.0, 580.0, 640.0, 600.0],
        }
    )

    tel_rows = []
    for row in flights.itertuples(index=False):
        climb_dur = 4 if row.altitude_m <= 25 else 8
        total_dur = int(row.duration_s)
        for t in range(total_dur):
            if t < climb_dur:
                phase = "Take-off"
                power = 580.0
            elif t < total_dur - 4:
                phase = "Cruise"
                power = 480.0
            else:
                phase = "Landing"
                power = 440.0
            tel_rows.append(
                {
                    "flight": row.flight,
                    "t_since_takeoff_s": float(t),
                    "phase": phase,
                    "power_w": power,
                }
            )
    return pd.DataFrame(tel_rows), flights


@pytest.mark.parametrize("order", ["altitude", "speed", "payload", "cluster"])
@pytest.mark.parametrize("color", ["phase", "power"])
def test_build_flight_time_heatmap_modes_and_group_separators(order: str, color: str) -> None:
    tel, fl = _sample_heatmap_data()
    fig = build_flight_time_heatmap(
        telemetry=tel,
        flights=fl,
        order=order,
        color=color,
        include_other_routes=False,
        k=2,
    )
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    trace = fig.data[0]
    assert isinstance(trace, go.Heatmap)
    assert np.asarray(trace.z).shape[0] == 4
    assert len(fig.layout.shapes) >= 1
    assert len(fig.layout.annotations) >= 2


def test_include_other_routes_toggles_r2_r7_and_climb_widens() -> None:
    tel, fl = _sample_heatmap_data()
    fig_all = build_flight_time_heatmap(
        telemetry=tel,
        flights=fl,
        order="altitude",
        color="phase",
        include_other_routes=True,
    )
    assert np.asarray(fig_all.data[0].z).shape[0] == 5

    climb = summarize_climb_band_by_altitude(tel, fl)
    assert climb["max_climb_s"] > climb["min_climb_s"]


def test_build_flight_time_heatmap_rejects_invalid_args() -> None:
    tel, fl = _sample_heatmap_data()
    with pytest.raises(ValueError):
        build_flight_time_heatmap(tel, fl, order="invalid")
    with pytest.raises(ValueError):
        build_flight_time_heatmap(tel, fl, color="invalid")
