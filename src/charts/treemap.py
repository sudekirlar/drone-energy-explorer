"""G5 · Experiment tree: the settings as a treemap, icicle or sunburst (owner: Platform).

The R1 experiment is a grid: 3 payloads x 4 altitudes x 5 speeds = 60 settings, each flown about
three times. Arranged as a tree, the grid becomes three levels under one root, and every leaf is
one setting:

    size of a box   number of flights (nearly equal, because the design is balanced)
    colour          median energy per kilometre (Wh/km) of the flights in the box

The order of the levels is our choice, not a property of the data, so it is a parameter.

No Streamlit here (tests/test_architecture.py).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src import theme

# level -> (flights column, unit after the value, name used in sentences)
LEVELS: dict[str, tuple[str, str, str]] = {
    "payload": ("payload_g", " g", "payload"),
    "altitude": ("altitude_m", " m", "altitude"),
    "speed": ("speed_mps", " m/s", "speed"),
}
LAYOUTS = ("treemap", "icicle", "sunburst")
ROOT = "All R1 flights"
SEP = "|"
METRIC = "wh_per_km"


def design_flights(flights: pd.DataFrame) -> pd.DataFrame:
    """Only the R1 design flights form the grid; other routes would add unbalanced leaves."""
    return flights.loc[flights["in_design"].astype(bool)].dropna(
        subset=[c for c, _, _ in LEVELS.values()] + [METRIC]
    )


def _value_text(value, level: str) -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return f"{value}{LEVELS[level][1]}"


def tree_nodes(flights: pd.DataFrame, order: tuple[str, ...]) -> pd.DataFrame:
    """One row per box: id, parent, label, number of flights and median Wh/km.

    Ids are paths ("All R1 flights|0 g|25 m"), so the same value under two parents stays two
    boxes; "|" because "/" appears in "m/s". ``depth`` is 0 for the root and 3 for a setting.
    Children are listed in ascending order of their value.
    """
    grid = design_flights(flights)
    columns = [LEVELS[level][0] for level in order]
    rows = [
        {
            "id": ROOT,
            "parent": "",
            "label": ROOT,
            "path": ROOT,
            "level": "",
            "depth": 0,
            "flights": len(grid),
            "median": grid[METRIC].median(),
        }
    ]
    for depth in range(1, len(order) + 1):
        keys = columns[:depth]
        stats = (
            grid.groupby(keys)[METRIC]
            .agg(flights="size", median="median")
            .reset_index()
            .sort_values(keys)
        )
        for rec in stats.itertuples(index=False):
            values = [getattr(rec, c) for c in keys]
            parts = [_value_text(v, lvl) for v, lvl in zip(values, order, strict=False)]
            rows.append(
                {
                    "id": SEP.join([ROOT, *parts]),
                    "parent": SEP.join([ROOT, *parts[:-1]]),
                    "label": parts[-1],
                    "path": " · ".join(parts),
                    "level": LEVELS[order[depth - 1]][2],
                    "depth": depth,
                    "flights": int(rec.flights),
                    "median": float(rec.median),
                }
            )
    return pd.DataFrame(rows)


def build_treemap(
    flights: pd.DataFrame,
    order: tuple[str, ...] = ("payload", "altitude", "speed"),
    layout: str = "treemap",
) -> go.Figure:
    """The experiment grid as a tree, drawn as a treemap, an icicle or a sunburst."""
    fig = go.Figure()
    nodes = tree_nodes(flights, order)
    if nodes.at[0, "flights"] == 0:
        fig.add_annotation(text="No R1 flights match the filters.", showarrow=False)
        fig.update_layout(xaxis_visible=False, yaxis_visible=False, height=200)
        return fig

    trace_type = {"treemap": go.Treemap, "icicle": go.Icicle, "sunburst": go.Sunburst}[layout]
    extra = {}
    if layout == "treemap":
        extra["tiling"] = dict(pad=2)
    else:
        # 60 settings do not fit as thin icicle rows or a thin outer ring, so these two open
        # with two levels below the root; clicking a box shows the level beneath it.
        extra["maxdepth"] = 3
    if layout != "sunburst":
        extra["pathbar"] = dict(visible=True)
    fig.add_trace(
        trace_type(
            ids=nodes["id"],
            parents=nodes["parent"],
            labels=nodes["label"],
            values=nodes["flights"],
            branchvalues="total",
            sort=False,
            marker=dict(
                colors=nodes["median"].round(1),
                colorscale=theme.PALETTES["viridis"],
                showscale=True,
                colorbar=dict(title=dict(text="Wh/km<br>(median)"), thickness=12),
            ),
            customdata=nodes[["path", "median", "flights"]],
            # Treemap boxes are small, so the unit stays on the colour bar there.
            texttemplate=(
                "%{label}<br>%{customdata[1]:.0f}"
                if layout == "treemap"
                else "%{label}<br>%{customdata[1]:.0f} Wh/km"
            ),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>median %{customdata[1]:.1f} Wh/km<br>"
                "%{customdata[2]} flights<extra></extra>"
            ),
            **extra,
        )
    )
    # Text that does not fit at 10 px is hidden instead of shrunk; hover still shows the values.
    fig.update_layout(
        height=560, margin=dict(l=10, r=10, t=40, b=10), uniformtext=dict(minsize=10, mode="hide")
    )
    return fig


# ---- finding -------------------------------------------------------------------------------


def _setting(row: pd.Series, order: tuple[str, ...]) -> str:
    """'0 g, 25 m and 10 m/s', always in the order payload, altitude, speed."""
    parts = row["path"].split(" · ")
    by_level = dict(zip(order, parts, strict=True))
    words = [by_level[level] for level in ("payload", "altitude", "speed")]
    return f"{words[0]}, {words[1]} and {words[2]}"


def _facts(row: pd.Series) -> str:
    """'28.1 Wh/km, 3 flights'; a single flight is said in words, because it is a weak value."""
    n = int(row["flights"])
    return f"{row['median']:.1f} Wh/km, " + ("a single flight" if n == 1 else f"{n} flights")


def describe_treemap(
    flights: pd.DataFrame, order: tuple[str, ...] = ("payload", "altitude", "speed")
) -> str | None:
    """Two sentences: the cheapest and the most expensive setting on screen, and how far the
    median spreads at the top level (which changes with the level order)."""
    nodes = tree_nodes(flights, order)
    if nodes.at[0, "flights"] == 0:
        return None
    leaves = nodes.loc[nodes["depth"] == len(order)]
    cheap = leaves.loc[leaves["median"].idxmin()]
    dear = leaves.loc[leaves["median"].idxmax()]

    if len(leaves) == 1:
        text = f"Only one setting is on screen: {_setting(cheap, order)} ({_facts(cheap)})."
    else:
        text = (
            f"The cheapest setting on screen is {_setting(cheap, order)} ({_facts(cheap)}), and "
            f"the most expensive is {_setting(dear, order)} ({_facts(dear)}), "
            f"{dear['median'] / cheap['median']:.1f} times as much."
        )

    top = nodes.loc[nodes["depth"] == 1]
    if len(top) > 1:
        lo, hi = top.loc[top["median"].idxmin()], top.loc[top["median"].idxmax()]
        text += (
            f" At the top level ({LEVELS[order[0]][2]}), the median goes from "
            f"{lo['median']:.1f} Wh/km at {lo['label']} to {hi['median']:.1f} Wh/km at "
            f"{hi['label']}."
        )
    return text
