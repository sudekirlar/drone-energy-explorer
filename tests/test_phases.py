"""Tests for the estimated flight phases (src/data/phases.py).

A synthetic R1-like flight is built piece by piece (ground, spool-up, climb, three legs of a
triangle with two turns, descent), so we know exactly which phases the rule should find.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data import phases, schema

DT = 0.1  # s, close to the raw sampling interval
TARGET = 10.0  # m/s

# (duration s, power W, ground speed at start, at end, heading deg, vertical speed m/s)
TRIANGLE = [
    (3, 5, 0, 0, 0, 0),  # ground
    (4, 450, 0, 0, 0, 0),  # spool-up
    (10, 600, 0, 0, 0, 2.5),  # climb to 25 m
    (2, 500, 0, 0, 0, 0),  # hover
    (3, 550, 0, TARGET, 60, 0),  # accelerate
    (12, 500, TARGET, TARGET, 60, 0),  # leg 1
    (3, 550, TARGET, 0.5, 60, 0),  # slow down at WP 1
    (3, 550, 0.5, TARGET, 200, 0),  # accelerate after WP 1
    (15, 500, TARGET, TARGET, 200, 0),  # leg 2
    (3, 550, TARGET, 0.5, 200, 0),  # slow down at WP 2
    (3, 550, 0.5, TARGET, 320, 0),  # accelerate after WP 2
    (12, 500, TARGET, TARGET, 320, 0),  # leg 3
    (3, 550, TARGET, 0, 320, 0),  # slow down at home
    (2, 500, 0, 0, 0, 0),  # hover
    (17, 480, 0, 0, 0, -1.5),  # descent
    (3, 5, 0, 0, 0, 0),  # ground
]

EXPECTED = [
    "Ground",
    "Spool-up",
    "Climb",
    "Speed change",
    "Straight leg",
    "WP turn",
    "Straight leg",
    "WP turn",
    "Straight leg",
    "Speed change",
    "Descent",
    "Ground",
]


def make_flight(pieces: list[tuple], flight: int = 1) -> pd.DataFrame:
    """Raw-rate samples with the columns clean_telemetry produces."""
    rows = []
    for duration, power, gs0, gs1, heading, vz in pieces:
        steps = int(round(duration / DT))
        for gs in np.linspace(gs0, gs1, steps, endpoint=False):
            rows.append((power, gs, heading, vz))
    power, gs, heading, vz = (np.array(c, dtype=float) for c in zip(*rows, strict=True))
    t = np.arange(len(power)) * DT
    rad = np.radians(heading)
    east = np.cumsum(gs * np.sin(rad) * DT)
    north = np.cumsum(gs * np.cos(rad) * DT)
    alt = np.cumsum(vz * DT)
    energy = np.concatenate(([0.0], np.cumsum((power[1:] + power[:-1]) / 2 * DT / 3600)))
    return pd.DataFrame(
        {
            "flight": flight,
            "t_s": t,
            "lat_deg": 40.459 + north / 111_000,
            "lon_deg": -79.783 + east / 84_500,
            "east_m": east,
            "north_m": north,
            "alt_rel_m": alt,
            "ground_speed_mps": gs,
            "vertical_speed_mps": vz,
            "course_deg": np.degrees(rad) % 360,
            "airspeed_mps": gs + 1.8,
            "voltage_v": 24.0,
            "current_a": power / 24.0,
            "power_w": power,
            "energy_wh": energy,
        }
    )


def run_labels(labelled: pd.DataFrame) -> list[str]:
    sub = labelled["sub_phase"].to_numpy()
    return [str(sub[a]) for a, _ in phases._runs(sub)]


# ---- the rule -----------------------------------------------------------------------------------


def test_triangle_flight_gets_the_expected_phase_sequence():
    labelled = phases.label_phases(make_flight(TRIANGLE), TARGET)
    assert run_labels(labelled) == EXPECTED


def test_main_phase_follows_the_sub_phase():
    labelled = phases.label_phases(make_flight(TRIANGLE), TARGET)
    assert set(labelled["phase"]) <= set(schema.PHASES)
    assert (labelled["phase"] == labelled["sub_phase"].map(schema.SUB_PHASE_PARENT)).all()


def test_time_since_take_off_starts_at_the_climb():
    labelled = phases.label_phases(make_flight(TRIANGLE), TARGET)
    first_climb = labelled.loc[labelled["sub_phase"] == "Climb", "t_since_takeoff_s"].iloc[0]
    assert first_climb == pytest.approx(0.0)
    assert labelled["t_since_takeoff_s"].iloc[0] < 0


def test_short_speed_dip_inside_a_leg_is_merged():
    pieces = list(TRIANGLE)
    i = pieces.index((12, 500, TARGET, TARGET, 60, 0))
    pieces[i : i + 1] = [
        (6, 500, TARGET, TARGET, 60, 0),
        (1, 500, 6.0, 6.0, 60, 0),  # 1 s below 80 % of the target speed
        (5, 500, TARGET, TARGET, 60, 0),
    ]
    labelled = phases.label_phases(make_flight(pieces), TARGET)
    assert run_labels(labelled) == EXPECTED


def test_turn_below_the_angle_threshold_is_a_speed_change():
    pieces = [list(p) for p in TRIANGLE]
    for p in pieces[7:10]:  # leg 2 and its ramps point almost like leg 1
        p[4] = 90
    labelled = phases.label_phases(make_flight([tuple(p) for p in pieces]), TARGET)
    assert phases.phase_summary(phases.phase_energy(labelled), labelled)["wp_turn_count"] == 1


def test_climbing_while_moving_is_sloped_cruise():
    pieces = [list(p) for p in TRIANGLE]
    pieces[8][5] = 1.5  # leg 2 climbs 22.5 m in 15 s
    labelled = phases.label_phases(make_flight([tuple(p) for p in pieces]), TARGET)
    labels = run_labels(labelled)
    assert "Sloped cruise" in labels
    assert labels.count("WP turn") == 2


# ---- tables -------------------------------------------------------------------------------------


def test_phase_energies_add_up_to_the_flight_total():
    flight = make_flight(TRIANGLE)
    energy = phases.phase_energy(phases.label_phases(flight, TARGET))
    assert energy["energy_wh"].sum() == pytest.approx(flight["energy_wh"].iloc[-1], abs=1e-9)
    assert energy["duration_s"].sum() == pytest.approx(flight["t_s"].iloc[-1], abs=1e-9)


def test_phase_energy_has_every_sub_phase_with_zeros_kept():
    energy = phases.phase_energy(phases.label_phases(make_flight(TRIANGLE), TARGET))
    assert energy["sub_phase"].tolist() == list(schema.SUB_PHASES)
    assert energy.set_index("sub_phase").loc["Sloped cruise", "energy_wh"] == 0.0


def test_waypoints_are_home_then_the_two_turns():
    labelled = phases.label_phases(make_flight(TRIANGLE), TARGET)
    wp = phases.find_waypoints(labelled)
    assert wp["wp_index"].tolist() == [0, 1, 2]
    assert np.isnan(wp["turn_angle_deg"].iloc[0])
    assert wp["turn_angle_deg"].iloc[1:].tolist() == pytest.approx([140, 120], abs=1)


def test_summary_columns():
    labelled = phases.label_phases(make_flight(TRIANGLE), TARGET)
    summary = phases.phase_summary(phases.phase_energy(labelled), labelled)
    assert summary["wp_turn_count"] == 2
    assert summary["climb_power_w"] == pytest.approx(600, abs=1)
    assert 500 <= summary["cruise_power_w"] <= 550


def test_phases_reach_the_1hz_table_one_row_each():
    flight = make_flight(TRIANGLE)
    labelled = phases.label_phases(flight, TARGET)
    # Same reduction as build_processed: the last raw sample of every whole second.
    one_hz = flight.assign(t_s=np.floor(flight["t_s"])).groupby("t_s", as_index=False).last()
    out = phases.add_phases_to_1hz(one_hz, labelled)
    assert len(out) == len(one_hz)
    assert out[["phase", "sub_phase", "t_since_takeoff_s"]].notna().all().all()
