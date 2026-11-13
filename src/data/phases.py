"""Estimated flight phases, phase energy and waypoints (task T6, owner: Platform).

Input is the raw-rate telemetry written by ``src/data/build_processed.py`` (one row per raw
sample, produced by ``preprocess.clean_telemetry``). The rule (chart guide, "Uçuşun evreleri";
decision D6) labels every sample with one of eight sub-phases:

    Ground        power below 60 W
    Spool-up      motors on, before the climb starts
    Climb         before the first horizontal motion: vertical speed > 0.5 and ground speed < 1.5
    Straight leg  ground speed >= 80 % of the target speed
    Sloped cruise moving (ground speed >= 1.5) for >= 10 s while altitude changes by > 10 m
    WP turn       between two cruise legs whose directions differ by more than 45 degrees
    Speed change  every other part of the motion (accelerating, slowing down, hovering)
    Descent       after the last horizontal motion: vertical speed < -0.5 and ground speed < 1.5,
                  until the motors stop (touchdown included)

Pieces shorter than 2 s are merged into the previous piece. A leg's direction is the direction
of the straight line from its first to its last point, so GPS noise in single samples does not
create false turns.

Energy conservation holds by construction: the energy between two consecutive samples is booked
to the sub-phase of the first one, so the sub-phase energies of a flight add up to its total.

This module only computes: it takes tables and returns tables, and never reads or writes files.
``src/data/pipeline.py`` runs it between the cleaning step and the contract check. No Streamlit
here (see tests/test_architecture.py).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.data import schema

CRUISE_SUB_PHASES = ("Straight leg", "Sloped cruise")
PLATFORM_FLIGHT_COLUMNS = ["cruise_power_w", "climb_power_w", "wp_turn_count"]
PLATFORM_TELEMETRY_COLUMNS = ["t_since_takeoff_s", "phase", "sub_phase"]


@dataclass(frozen=True)
class Thresholds:
    """Every number the rule uses, in one place (changed together in the sensitivity check)."""

    ground_power_w: float = 60.0
    vertical_speed_mps: float = 0.5
    hover_ground_speed_mps: float = 1.5
    cruise_speed_ratio: float = 0.8
    min_segment_s: float = 2.0
    turn_angle_deg: float = 45.0
    sloped_min_duration_s: float = 10.0
    sloped_min_alt_change_m: float = 10.0


DEFAULT = Thresholds()


# ---- small helpers ------------------------------------------------------------------------------


def _runs(values: np.ndarray) -> list[tuple[int, int]]:
    """(start, stop) index pairs of consecutive equal values; stop is exclusive."""
    if len(values) == 0:
        return []
    change = np.flatnonzero(values[1:] != values[:-1]) + 1
    starts = np.concatenate(([0], change))
    stops = np.concatenate((change, [len(values)]))
    return list(zip(starts.tolist(), stops.tolist(), strict=True))


def _duration(t: np.ndarray, start: int, stop: int) -> float:
    """Time covered by samples start..stop-1, up to the sample that follows them."""
    end = t[stop] if stop < len(t) else t[-1]
    return float(end - t[start])


def _sustained(mask: np.ndarray, t: np.ndarray, min_s: float) -> list[tuple[int, int]]:
    """True runs of ``mask`` that last at least ``min_s`` seconds."""
    return [(a, b) for a, b in _runs(mask) if mask[a] and _duration(t, a, b) >= min_s]


def _direction_deg(east: np.ndarray, north: np.ndarray, start: int, stop: int) -> float:
    """Direction of travel from the first to the last sample of a piece (0 = north)."""
    de = east[stop - 1] - east[start]
    dn = north[stop - 1] - north[start]
    return float(np.degrees(np.arctan2(de, dn)) % 360)


def _angle_between(a_deg: float, b_deg: float) -> float:
    """Smallest angle between two directions, 0-180 degrees."""
    diff = abs(a_deg - b_deg) % 360
    return float(min(diff, 360 - diff))


def _merge_short(labels: np.ndarray, t: np.ndarray, min_s: float) -> np.ndarray:
    """Give every piece shorter than ``min_s`` the label of the piece before it."""
    out = labels.copy()
    for i, (a, b) in enumerate(_runs(labels)):
        if i > 0 and _duration(t, a, b) < min_s:
            out[a:b] = out[a - 1]
    return out


# ---- the rule -----------------------------------------------------------------------------------


def label_phases(
    flight: pd.DataFrame, target_speed_mps: float, th: Thresholds = DEFAULT
) -> pd.DataFrame:
    """Add ``sub_phase``, ``phase`` and ``t_since_takeoff_s`` to one flight's raw-rate samples."""
    df = flight.sort_values("t_s").reset_index(drop=True)
    t = df["t_s"].to_numpy(dtype=float)
    power = df["power_w"].to_numpy(dtype=float)
    gs = df["ground_speed_mps"].to_numpy(dtype=float)
    vz = df["vertical_speed_mps"].to_numpy(dtype=float)
    alt = df["alt_rel_m"].to_numpy(dtype=float)
    east = df["east_m"].to_numpy(dtype=float)
    north = df["north_m"].to_numpy(dtype=float)
    n = len(df)

    labels = np.full(n, "Ground", dtype=object)
    powered = power >= th.ground_power_w
    idx = np.arange(n)
    takeoff_t = t[0]

    if powered.any():
        first_on, last_on = int(idx[powered][0]), int(idx[powered][-1])
        on = (idx >= first_on) & (idx <= last_on)
        moving_runs = _sustained(on & (gs >= th.hover_ground_speed_mps), t, th.min_segment_s)
        first_move = moving_runs[0][0] if moving_runs else last_on + 1
        last_move = moving_runs[-1][1] - 1 if moving_runs else last_on

        # Take-off: spool-up until the climb starts, then the vertical climb.
        climbing = on & (idx < first_move) & (vz > th.vertical_speed_mps)
        climbing &= gs < th.hover_ground_speed_mps
        climb_runs = _sustained(climbing, t, 1.0)
        if climb_runs:
            climb_start, climb_end = climb_runs[0][0], climb_runs[-1][1]
        else:  # no vertical climb found: the take-off is the first powered sample
            climb_start = climb_end = first_on
        labels[first_on:climb_start] = "Spool-up"
        labels[climb_start:climb_end] = "Climb"
        labels[climb_end:first_move] = "Speed change"  # hover and acceleration before leg 1
        takeoff_t = t[climb_start]

        # Landing: the vertical descent after the last motion, until the motors stop.
        if moving_runs:
            descending = on & (idx > last_move) & (vz < -th.vertical_speed_mps)
            descending &= gs < th.hover_ground_speed_mps
            descent_runs = _sustained(descending, t, 1.0)
            descent_start = descent_runs[0][0] if descent_runs else last_on + 1
            labels[last_move + 1 : descent_start] = "Speed change"
            labels[descent_start : last_on + 1] = "Descent"

            _label_motion(labels, moving_runs, t, gs, alt, east, north, target_speed_mps, th)

        labels[~powered] = "Ground"

    labels = _merge_short(labels, t, th.min_segment_s)

    out = df.copy()
    out["sub_phase"] = labels.astype(str)
    out["phase"] = out["sub_phase"].map(schema.SUB_PHASE_PARENT)
    out["t_since_takeoff_s"] = t - takeoff_t
    return out


def _label_motion(
    labels: np.ndarray,
    moving_runs: list[tuple[int, int]],
    t: np.ndarray,
    gs: np.ndarray,
    alt: np.ndarray,
    east: np.ndarray,
    north: np.ndarray,
    target_speed_mps: float,
    th: Thresholds,
) -> None:
    """Label everything between the first and the last horizontal motion (in place)."""
    first_move, end_move = moving_runs[0][0], moving_runs[-1][1]
    labels[first_move:end_move] = "Speed change"

    legs: list[tuple[int, int]] = []
    for a, b in moving_runs:
        sloped = (
            _duration(t, a, b) >= th.sloped_min_duration_s
            and abs(alt[b - 1] - alt[a]) > th.sloped_min_alt_change_m
        )
        if sloped:
            labels[a:b] = "Sloped cruise"
            legs.append((a, b))
            continue
        fast = np.zeros(len(t), dtype=bool)
        fast[a:b] = gs[a:b] >= th.cruise_speed_ratio * target_speed_mps
        for la, lb in _sustained(fast, t, th.min_segment_s):
            labels[la:lb] = "Straight leg"
            legs.append((la, lb))

    for (a1, b1), (a2, b2) in zip(legs, legs[1:], strict=False):
        turn = _angle_between(
            _direction_deg(east, north, a1, b1), _direction_deg(east, north, a2, b2)
        )
        labels[b1:a2] = "WP turn" if turn > th.turn_angle_deg else "Speed change"


# ---- tables from labelled samples ---------------------------------------------------------------


def phase_energy(labelled: pd.DataFrame) -> pd.DataFrame:
    """Energy and time per sub-phase for one labelled flight; all eight sub-phases, zeros kept.

    Absent sub-phases get a zero row, so averaging over flights counts them as zero instead of
    leaving them out (otherwise the mean "Sloped cruise" energy would be an average of R7 only).
    """
    energy = labelled["energy_wh"].to_numpy(dtype=float)
    t = labelled["t_s"].to_numpy(dtype=float)
    frame = pd.DataFrame(
        {
            "sub_phase": labelled["sub_phase"].to_numpy(),
            "energy_wh": np.diff(energy, append=energy[-1]),  # interval i -> i+1, booked to i
            "duration_s": np.diff(t, append=t[-1]),
        }
    )
    sums = frame.groupby("sub_phase")[["energy_wh", "duration_s"]].sum()
    sums = sums.reindex(list(schema.SUB_PHASES), fill_value=0.0).reset_index()
    sums.insert(0, "flight", int(labelled["flight"].iloc[0]))
    sums.insert(1, "phase", sums["sub_phase"].map(schema.SUB_PHASE_PARENT))
    return sums[["flight", "phase", "sub_phase", "energy_wh", "duration_s"]]


def find_waypoints(labelled: pd.DataFrame) -> pd.DataFrame:
    """Home (index 0, at take-off) and the slowest point of every WP turn, in flight order."""
    sub = labelled["sub_phase"].to_numpy()
    t = labelled["t_s"].to_numpy(dtype=float)
    gs = labelled["ground_speed_mps"].to_numpy(dtype=float)
    east = labelled["east_m"].to_numpy(dtype=float)
    north = labelled["north_m"].to_numpy(dtype=float)
    runs = _runs(sub)
    legs = [(a, b) for a, b in runs if sub[a] in CRUISE_SUB_PHASES]

    takeoff = int(np.argmin(np.abs(labelled["t_since_takeoff_s"].to_numpy(dtype=float))))
    picks: list[tuple[int, float]] = [(takeoff, np.nan)]
    for a, b in runs:
        if sub[a] != "WP turn":
            continue
        before = [leg for leg in legs if leg[1] <= a]
        after = [leg for leg in legs if leg[0] >= b]
        angle = np.nan
        if before and after:
            angle = _angle_between(
                _direction_deg(east, north, *before[-1]), _direction_deg(east, north, *after[0])
            )
        picks.append((a + int(np.argmin(gs[a:b])), angle))

    rows = labelled.iloc[[i for i, _ in picks]]
    return pd.DataFrame(
        {
            "flight": rows["flight"].to_numpy(dtype=int),
            "wp_index": np.arange(len(picks)),
            "lat_deg": rows["lat_deg"].to_numpy(dtype=float),
            "lon_deg": rows["lon_deg"].to_numpy(dtype=float),
            "east_m": rows["east_m"].to_numpy(dtype=float),
            "north_m": rows["north_m"].to_numpy(dtype=float),
            "t_s": t[[i for i, _ in picks]],
            "turn_angle_deg": [a for _, a in picks],
        }
    )


def phase_summary(energy: pd.DataFrame, labelled: pd.DataFrame) -> dict:
    """The three Platform columns of the flights table for one flight."""
    by_sub = energy.set_index("sub_phase")

    def mean_power(sub_phases: list[str]) -> float:
        e = by_sub.loc[sub_phases, "energy_wh"].sum()
        d = by_sub.loc[sub_phases, "duration_s"].sum()
        return float(e * 3600 / d) if d > 0 else float("nan")

    sub = labelled["sub_phase"].to_numpy()
    turns = sum(1 for a, _ in _runs(sub) if sub[a] == "WP turn")
    return {
        "flight": int(labelled["flight"].iloc[0]),
        "cruise_power_w": mean_power(list(CRUISE_SUB_PHASES)),
        "climb_power_w": mean_power(["Climb"]),
        "wp_turn_count": int(turns),
    }


# ---- every flight --------------------------------------------------------------------------------


def label_all(
    raw: pd.DataFrame, flights: pd.DataFrame, th: Thresholds = DEFAULT
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run the rule on every flight: (labelled samples, phase_energy, waypoints, summary)."""
    speeds = flights.set_index("flight")["speed_mps"]
    labelled, energies, waypoints, summaries = [], [], [], []
    for flight_id, samples in raw.groupby("flight", sort=True):
        lab = label_phases(samples, float(speeds.loc[flight_id]), th)
        energy = phase_energy(lab)
        labelled.append(lab)
        energies.append(energy)
        waypoints.append(find_waypoints(lab))
        summaries.append(phase_summary(energy, lab))
    return (
        pd.concat(labelled, ignore_index=True),
        pd.concat(energies, ignore_index=True),
        pd.concat(waypoints, ignore_index=True),
        pd.DataFrame(summaries),
    )


def add_phases_to_1hz(telemetry_1hz: pd.DataFrame, labelled: pd.DataFrame) -> pd.DataFrame:
    """Fill the Platform columns of the 1 Hz table.

    build_processed keeps the last raw sample of every whole second, so the phase of a 1 Hz row
    is the phase of that same sample.
    """
    per_second = (
        labelled.assign(t_s=np.floor(labelled["t_s"]))
        .groupby(["flight", "t_s"], as_index=False)[["phase", "sub_phase"]]
        .last()
    )
    takeoff = (labelled["t_s"] - labelled["t_since_takeoff_s"]).groupby(labelled["flight"]).first()
    out = telemetry_1hz.drop(columns=PLATFORM_TELEMETRY_COLUMNS, errors="ignore")
    out = out.merge(per_second, on=["flight", "t_s"], how="left", validate="one_to_one")
    out["t_since_takeoff_s"] = out["t_s"] - out["flight"].map(takeoff)
    return out
