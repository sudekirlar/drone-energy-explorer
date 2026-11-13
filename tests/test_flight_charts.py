"""Fast synthetic checks for Data-owned graphics; no raw dataset required."""

import pandas as pd

from src.charts.route_map import build_route_map
from src.charts.space_time_cube import build_space_time_cube
from src.charts.timeline import build_timeline


def sample_telemetry():
    return pd.DataFrame(
        {
            "flight": [1, 1, 1, 2, 2, 2],
            "t_s": [0.0, 1.0, 2.0, 0.0, 1.0, 2.0],
            "lat_deg": [40.0, 40.0001, 40.0002] * 2,
            "lon_deg": [-79.0, -79.0001, -79.0002] * 2,
            "east_m": [0.0, 2.0, 4.0] * 2,
            "north_m": [0.0, 3.0, 6.0] * 2,
            "power_w": [20.0, 40.0, 30.0] * 2,
            "ground_speed_mps": [0.0, 2.0, 1.0] * 2,
            "airspeed_mps": [0.0, 3.0, 2.0] * 2,
            "alt_rel_m": [0.0, 2.0, 3.0] * 2,
            "voltage_v": [24.0, 23.5, 23.4] * 2,
            "phase": ["Ground", "Take-off", "Cruise"] * 2,
            "sub_phase": ["Ground", "Climb", "Straight leg"] * 2,
        }
    )


def test_route_map_handles_a_and_b():
    fig = build_route_map(sample_telemetry(), None, [1, 2])
    assert len(fig.data) >= 4


def test_route_map_handles_unlabelled_phases():
    telemetry = sample_telemetry().drop(columns=["phase", "sub_phase"])
    fig = build_route_map(telemetry, None, [1], "Estimated phase")
    assert len(fig.data) >= 2


def test_cube_has_time_and_altitude_modes():
    for mode in ["Time (s)", "Relative altitude (m)"]:
        fig = build_space_time_cube(sample_telemetry(), [1, 2], mode)
        assert len(fig.data) == 2


def test_timeline_four_panels_and_optional_phases():
    fig = build_timeline(sample_telemetry(), 1, True)
    assert len(fig.data) == 5
    plain = build_timeline(sample_telemetry().drop(columns=["phase", "sub_phase"]), 1)
    assert len(plain.data) == 5
