"""Unit tests for src/charts/splom.py."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from src.charts.splom import SPLOM_AXES, build_splom
from src.theme import PALETTES


def _sample_splom_flights(n: int = 18) -> tuple[pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(11)
    df = pd.DataFrame(
        {
            "flight": np.arange(1, n + 1),
            "payload_g": np.tile([0, 250, 500], n // 3),
            "speed_mps": np.repeat([4, 8, 12], n // 3),
            "altitude_m": np.tile([25.0, 50.0, 100.0], n // 3),
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


@pytest.mark.parametrize("color_by", ["payload", "cluster", "altitude"])
def test_build_splom_lower_triangle_hidden_diagonal_and_select_mode(color_by: str) -> None:
    df, labels = _sample_splom_flights()
    fig = build_splom(df, color_by=color_by, labels=labels)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 3
    assert fig.layout.dragmode == "select"

    trace = fig.data[0]
    assert isinstance(trace, go.Splom)
    assert trace.showupperhalf is False
    assert trace.diagonal.visible is False

    dim_labels = [d.label for d in trace.dimensions]
    assert len(SPLOM_AXES) == 5
    assert len(dim_labels) == 5
    assert "Voltage drop (V)" in dim_labels
    assert all("anemometer" not in lbl.lower() for lbl in dim_labels)
    assert all("energy (wh)" not in lbl.lower() for lbl in dim_labels)


def test_build_splom_maps_colors_by_value_not_position() -> None:
    df, _ = _sample_splom_flights()
    filtered = df[df["payload_g"] != 0].reset_index(drop=True)
    fig = build_splom(filtered, color_by="payload")

    trace_250 = next(t for t in fig.data if t.name == "250 g")
    assert trace_250.marker.color == PALETTES["payload"][250]


def test_build_splom_rejects_unknown_color_mode() -> None:
    df, _ = _sample_splom_flights()
    with pytest.raises(ValueError):
        build_splom(df, color_by="route")
