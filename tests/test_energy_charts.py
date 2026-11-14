"""Fast synthetic checks for the Energy & Experimental Conditions charts; no real data needed."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.charts import payload_heatmap, sankey, treemap
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


# ---- G5 treemap ----------------------------------------------------------------------------

ORDER = ("payload", "altitude", "speed")


def _grid() -> pd.DataFrame:
    """A full 3 x 4 x 5 design grid with one flight per setting, plus one R7 flight.

    Wh/km grows with payload and altitude and falls with speed, so the cheapest setting is
    0 g, 25 m, 12 m/s and the most expensive is 500 g, 100 m, 4 m/s.
    """
    rows, flight = [], 1
    for p in (0, 250, 500):
        for a in (25.0, 50.0, 75.0, 100.0):
            for s in (4, 6, 8, 10, 12):
                whkm = 30 + p / 50 + a / 5 - s
                rows.append((flight, p, a, s, True, whkm))
                flight += 1
    rows.append((278, 0, np.nan, 10, False, 20.0))
    return pd.DataFrame(
        rows, columns=["flight", "payload_g", "altitude_m", "speed_mps", "in_design", "wh_per_km"]
    )


def test_tree_has_root_three_levels_and_sixty_settings() -> None:
    nodes = treemap.tree_nodes(_grid(), ORDER)
    assert nodes["depth"].value_counts().sort_index().tolist() == [1, 3, 12, 60]
    assert nodes["id"].is_unique
    assert nodes.at[0, "flights"] == 60  # the R7 flight is not part of the grid


def test_every_box_holds_the_flights_of_its_children() -> None:
    nodes = treemap.tree_nodes(_grid(), ORDER).set_index("id")
    children = nodes.reset_index().groupby("parent")["flights"].sum()
    for parent, total in children.items():
        if parent:
            assert nodes.at[parent, "flights"] == total


def test_order_decides_the_top_level() -> None:
    nodes = treemap.tree_nodes(_grid(), ("speed", "altitude", "payload"))
    assert nodes.loc[nodes["depth"] == 1, "label"].tolist() == [
        "4 m/s",
        "6 m/s",
        "8 m/s",
        "10 m/s",
        "12 m/s",
    ]


def test_every_layout_draws() -> None:
    for layout in treemap.LAYOUTS:
        fig = treemap.build_treemap(_grid(), ORDER, layout)
        assert fig.data[0].type == layout
        assert len(fig.data[0].ids) == 76


def test_tree_finding_names_cheapest_and_dearest_setting() -> None:
    text = treemap.describe_treemap(_grid(), ORDER)
    assert text.startswith(
        "The cheapest setting on screen is 0 g, 25 m and 12 m/s (23.0 Wh/km, a single flight)"
    )
    assert (
        "the most expensive is 500 g, 100 m and 4 m/s (56.0 Wh/km, a single flight), "
        "2.4 times as much" in text
    )
    assert "At the top level (payload), the median goes from" in text
    # The setting is always written as payload, altitude, speed, whatever the level order.
    assert "0 g, 25 m and 12 m/s" in treemap.describe_treemap(
        _grid(), ("speed", "altitude", "payload")
    )


def test_tree_with_no_design_flights() -> None:
    only_r7 = _grid().loc[lambda d: ~d["in_design"]]
    assert treemap.describe_treemap(only_r7, ORDER) is None
    assert len(treemap.build_treemap(only_r7, ORDER).data) == 0


# ---- G6 payload x speed heatmap + Random Forest -----------------------------------------------

METRICS = {
    "random_forest": {
        "cv": {"r2_mean": 0.788, "r2_std": 0.008, "mae_mean": 14.9, "mae_std": 0.3},
        "grouped_cv": {"r2": 0.760, "mae": 15.4, "n_groups": 60},
    },
    "linear_regression": {
        "cv": {"r2_mean": 0.772, "r2_std": 0.0015, "mae_mean": 15.4, "mae_std": 0.03},
        "grouped_cv": {"r2": 0.746, "mae": 16.1, "n_groups": 60},
    },
    "permutation_importance": [
        {"feature": "payload_g", "importance_mean": 1.59, "importance_std": 0.13},
        {"feature": "speed_mps", "importance_mean": 0.06, "importance_std": 0.04},
        {"feature": "altitude_m", "importance_mean": 0.01, "importance_std": 0.01},
    ],
}


def _model_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Two flights per (payload, speed) cell for 0/500 g and 4/12 m/s, plus one R7 flight.

    Measured power = 450 + payload/5 (+20 W at 12 m/s). The forest is 2 W off everywhere; the
    linear model misses the 12 m/s jump by 10 W.
    """
    rows, ml, flight = [], [], 1
    for p in (0, 500):
        for s in (4, 12):
            for _ in range(2):
                measured = 450 + p / 5 + (20 if s == 12 else 0)
                rows.append((flight, p, s, True))
                linear = measured - (10 if s == 12 else -5)
                ml.append((flight, measured, measured - 2, linear))
                flight += 1
    rows.append((278, 0, 10, False))
    flights = pd.DataFrame(rows, columns=["flight", "payload_g", "speed_mps", "in_design"])
    ml_payload = pd.DataFrame(
        ml, columns=["flight", "cruise_power_w", "rf_pred_w", "linear_pred_w"]
    )
    return flights, ml_payload


def test_heatmap_cells_hold_design_flights_only() -> None:
    fl, ml = _model_tables()
    cells = payload_heatmap.cell_table(payload_heatmap.model_data(fl, ml))
    assert len(cells) == 4
    assert cells["flights"].tolist() == [2, 2, 2, 2]
    assert cells["rf_gap"].tolist() == pytest.approx([2, 2, 2, 2])


def test_every_heatmap_view_draws_and_gaps_share_one_scale() -> None:
    fl, ml = _model_tables()
    scales = {}
    for view in payload_heatmap.VIEWS:
        trace = payload_heatmap.build_payload_heatmap(fl, ml, view).data[0]
        assert trace.z.shape == (2, 2)
        scales[view] = (trace.zmin, trace.zmax)
    assert scales["rf_gap"] == scales["lin_gap"]
    assert scales["observed"] == scales["rf"]


def test_heatmap_findings() -> None:
    fl, ml = _model_tables()
    observed = payload_heatmap.describe_payload_heatmap(fl, ml, "observed")
    assert observed.startswith(
        "Cruise power goes from 460 W at 0 g to 560 W at 500 g, about 50 W for every 250 g."
    )
    assert "lowest at 4 m/s (500 W) and highest at 12 m/s (520 W)" in observed
    gap = payload_heatmap.describe_payload_heatmap(fl, ml, "lin_gap")
    assert "+10.0 W at 0 g and 12 m/s, where it predicts too little" in gap
    assert "−5.0 W at 0 g and 4 m/s, where it predicts too much" in gap
    assert gap.endswith("On average, a cell is 7.5 W away from the measurement.")


def test_scores_and_signed_numbers() -> None:
    scores = payload_heatmap.model_scores(METRICS)
    assert scores["rf"] == "0.79 ± 0.01"
    assert scores["lin"] == "0.77 ± <0.01"
    assert scores["unseen"] == "0.76 / 0.75"
    assert payload_heatmap.model_scores({}) is None
    assert payload_heatmap._signed(-0.01) == "0.0 W"
    assert payload_heatmap._signed(-4.5) == "−4.5 W"


def test_side_charts_and_empty_inputs() -> None:
    fl, ml = _model_tables()
    assert len(payload_heatmap.build_prediction_scatter(fl, ml).data) == 3  # 2 payloads + line
    assert list(payload_heatmap.build_importance(METRICS).data[0].y) == [
        "Altitude",
        "Speed",
        "Payload",
    ]
    assert len(payload_heatmap.build_importance({}).data) == 0
    none = fl.iloc[0:0]
    assert payload_heatmap.describe_payload_heatmap(none, ml) is None
    assert len(payload_heatmap.build_payload_heatmap(none, ml).data) == 0
