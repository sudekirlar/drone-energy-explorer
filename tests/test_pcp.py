"""Unit tests for src/charts/pcp.py."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.charts.pcp import PCP_AXES, build_pcp


def _sample_pcp_flights(n: int = 18) -> tuple[pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(7)
    df = pd.DataFrame(
        {
            "flight": np.arange(1, n + 1),
            "payload_g": np.tile([0, 250, 500], n // 3),
            "speed_mps": np.repeat([4, 8, 12], n // 3),
            "altitude_m": np.tile([25.0, 50.0, 100.0], n // 3),
            "duration_s": np.repeat([320.0, 210.0, 150.0], n // 3),
            "energy_wh": np.linspace(35.0, 115.0, n),
            "wh_per_km": np.linspace(20.0, 55.0, n),
            "cruise_power_w": np.linspace(210.0, 410.0, n),
            "climb_power_w": np.linspace(290.0, 510.0, n),
            "start_voltage_v": np.full(n, 16.6),
            "end_voltage_v": np.linspace(15.4, 14.2, n),
            "anemometer_mps": rng.normal(5.0, 1.0, size=n),
        }
    )
    labels = pd.Series(np.tile(["G1", "G2", "G3"], n // 3))
    return df, labels


def test_build_pcp_has_nine_measures_plus_group_axis_and_legend() -> None:
    df, labels_k3 = _sample_pcp_flights()
    fig = build_pcp(df, labels_k3)

    assert isinstance(fig, go.Figure)
    trace = fig.data[0]
    assert isinstance(trace, go.Parcoords)

    dim_labels = [d.label for d in trace.dimensions]
    assert len(PCP_AXES) == 9
    assert len(dim_labels) == 10
    assert "Voltage drop (V)" in dim_labels
    assert "Group" in dim_labels
    assert all("anemometer" not in lbl.lower() for lbl in dim_labels)

    group_dim = trace.dimensions[-1]
    assert list(group_dim.range) == [1, 3]
    assert list(group_dim.ticktext) == ["Group 1", "Group 2", "Group 3"]
    assert len(fig.layout.annotations) == 1
    assert "Group 1" in fig.layout.annotations[0].text
