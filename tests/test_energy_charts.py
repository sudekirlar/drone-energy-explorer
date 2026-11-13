"""Fast synthetic checks for the Energy & Experimental Conditions charts; no real data needed."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.charts import sankey
from src.data import schema

# Energy (Wh) of one flight in each sub-phase, in schema.SUB_PHASES order.
# Ground, Spool-up, Climb, Straight leg, Sloped cruise, WP turn, Speed change, Descent
LOW = [0.05, 0.5, 2.0, 8.0, 0.0, 2.0, 1.0, 3.0]  # 16.55 Wh, 16.5 in the air
HIGH = [0.05, 0.5, 6.0, 8.0, 0.0, 2.0, 1.0, 7.0]  # 24.55 Wh, 24.5 in the air


def _tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Four R1 design flights at 25 m and 100 m, and one R7 flight without a target altitude."""
    flights = pd.DataFrame(
        {
            "flight": [1, 2, 3, 4, 278],
            "route": ["R1", "R1", "R1", "R1", "R7"],
            "payload_g": [0, 0, 500, 500, 0],
            "speed_mps": [4, 12, 4, 12, 10],
            "altitude_m": [25.0, 25.0, 100.0, 100.0, np.nan],
            "in_design": [True, True, True, True, False],
        }
    )
    per_flight = {1: LOW, 2: LOW, 3: HIGH, 4: HIGH, 278: LOW}
    rows = [
        {
            "flight": f,
            "phase": schema.SUB_PHASE_PARENT[s],
            "sub_phase": s,
            "energy_wh": e,
            "duration_s": 1.0,
        }
        for f, energies in per_flight.items()
        for s, e in zip(schema.SUB_PHASES, energies, strict=True)
    ]
    return pd.DataFrame(rows), flights


def _links(fig):
    t = fig.data[0]
    return list(t.link.source), list(t.link.target), list(t.link.value), list(t.node.label)


def test_bands_from_a_group_add_up_to_its_energy_in_the_air() -> None:
    pe, fl = _tables()
    fig = sankey.build_sankey(pe, fl, "altitude")
    src, _, val, labels = _links(fig)
    out = {labels[i]: sum(v for s, v in zip(src, val, strict=True) if s == i) for i in range(2)}
    assert out == pytest.approx({"25 m": 16.5, "100 m": 24.5})


def test_every_main_phase_passes_on_what_it_receives() -> None:
    pe, fl = _tables()
    src, tgt, val, labels = _links(sankey.build_sankey(pe, fl, "speed"))
    for i, name in enumerate(labels):
        if name in sankey.MAIN_PHASES:
            inflow = sum(v for t, v in zip(tgt, val, strict=True) if t == i)
            outflow = sum(v for s, v in zip(src, val, strict=True) if s == i)
            assert inflow == pytest.approx(outflow)


def test_node_hover_gives_flights_and_means() -> None:
    pe, fl = _tables()
    node = sankey.build_sankey(pe, fl, "altitude").data[0].node
    hover = dict(zip(node.label, node.customdata, strict=True))
    assert hover["25 m"] == "2 flights<br>16.5 Wh per flight in the air"
    # Landing: 3 Wh at 25 m and 7 Wh at 100 m -> mean 5 Wh of a mean 20.5 Wh in the air.
    assert hover["Landing"].startswith("on average 5.00 Wh per flight across the groups")
    assert "(24% of the energy in the air)" in hover["Landing"]


def test_ground_and_empty_sub_phases_are_not_drawn() -> None:
    pe, fl = _tables()
    labels = _links(sankey.build_sankey(pe, fl, "altitude"))[3]
    assert "Ground" not in labels
    assert "Sloped cruise" not in labels  # zero in every flight above
    assert "Waypoint turn" in labels


def test_settings_compare_design_flights_and_route_uses_all() -> None:
    pe, fl = _tables()
    _, counts = sankey.energy_by_group(pe, fl, "speed")
    assert counts.to_dict() == {4: 2, 12: 2}  # the R7 flight (10 m/s) is not a design flight
    _, counts = sankey.energy_by_group(pe, fl, "route")
    assert counts.to_dict() == {"R1": 4, "R7": 1}
    assert _links(sankey.build_sankey(pe, fl, "route"))[3][:2] == [
        "R1 (4 flights)",
        "R7 (1 flight)",
    ]


def test_finding_compares_the_lowest_and_highest_group() -> None:
    pe, fl = _tables()
    # Take-off + landing: 25 m = (0.5 + 2 + 3) / 16.5 = 33 %; 100 m = (0.5 + 6 + 7) / 24.5 = 55 %.
    assert sankey.describe_sankey(pe, fl, "altitude") == (
        "At 25 m, take-off and landing use 33% of a flight's energy. At 100 m, they use 55%."
    )
    assert sankey.describe_sankey(pe, fl, "payload") == (
        "A flight with 500 g uses 24.5 Wh in the air, which is 8.0 Wh more than a flight with "
        "0 g. The largest part of the difference is in take-off (4.0 Wh)."
    )
    assert "except R1 has only 1 flight." in sankey.describe_sankey(pe, fl, "route")


def test_one_group_and_no_flights() -> None:
    pe, fl = _tables()
    one = fl.loc[fl["altitude_m"] == 25.0]
    assert sankey.describe_sankey(pe, one, "altitude").startswith("In the 25 m group, cruise")
    empty = fl.iloc[0:0]
    assert sankey.describe_sankey(pe, empty, "altitude") is None
    assert len(sankey.build_sankey(pe, empty, "altitude").data) == 0
