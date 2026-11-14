"""Unit tests for src/charts/violin.py."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.charts.violin import (
    MAIN_PHASES,
    build_phase_payload_violin,
    compute_phase_payload_power,
    summarize_payload_effect,
)
from src.theme import PALETTES


def _sample_phase_telemetry() -> tuple[pd.DataFrame, pd.DataFrame]:
    flights_rows = []
    tel_rows = []
    flight_id = 1
    base_by_phase = {
        "Take-off": 530.0,
        "Cruise": 460.0,
        "Manoeuvre": 495.0,
        "Landing": 435.0,
    }
    for payload_g in (0, 250, 500):
        step_offset = (payload_g / 250.0) * 48.0
        for rep in range(3):
            flights_rows.append({"flight": flight_id, "payload_g": payload_g})
            for phase, base_w in base_by_phase.items():
                tel_rows.append(
                    {
                        "flight": flight_id,
                        "phase": phase,
                        "power_w": base_w + step_offset + (rep - 1) * 4.0,
                    }
                )
            tel_rows.append({"flight": flight_id, "phase": "Ground", "power_w": 25.0})
            flight_id += 1

    return pd.DataFrame(tel_rows), pd.DataFrame(flights_rows)


def test_compute_and_build_phase_payload_violin() -> None:
    tel, fl = _sample_phase_telemetry()
    phase_power = compute_phase_payload_power(tel, fl)

    assert set(phase_power["phase"].unique()) == set(MAIN_PHASES)
    assert "Ground" not in set(phase_power["phase"].unique())

    summary = summarize_payload_effect(phase_power)
    assert 45.0 <= summary["delta_w"] <= 52.0
    assert 8.5 <= summary["delta_pct"] <= 11.0

    fig_no_pts = build_phase_payload_violin(phase_power, show_points=False, cut_y_axis=True)
    assert isinstance(fig_no_pts, go.Figure)
    assert len(fig_no_pts.data) == 3
    assert fig_no_pts.layout.violinmode == "group"

    for trace, payload_g in zip(fig_no_pts.data, (0, 250, 500), strict=True):
        assert isinstance(trace, go.Violin)
        assert trace.name == f"{payload_g} g"
        assert trace.fillcolor == PALETTES["payload"][payload_g]
        assert trace.points is False

    assert any("cut axis" in ann.text.lower() for ann in fig_no_pts.layout.annotations)

    fig_pts = build_phase_payload_violin(phase_power, show_points=True, cut_y_axis=False)
    assert all(trace.points == "all" for trace in fig_pts.data)
    assert fig_pts.layout.yaxis.range[0] == 0.0
