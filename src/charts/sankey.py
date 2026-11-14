"""G4 · Energy budget Sankey: group of flights -> main phase -> sub-phase (owner: Platform).

A flight's energy is split between its estimated phases, and the parts add up to the flight's
total (energy conservation, D6/D14). A Sankey diagram assumes exactly this structure:

    left    groups of flights (altitude, speed, payload or route)
    middle  the four main phases: Take-off, Cruise, Manoeuvre, Landing
    right   the sub-phases of each main phase

A band from a group to a main phase is the energy that an average flight of that group spends
in that phase. The Ground sub-phase (motors idle before take-off and after landing, under 1% of
every flight) is left out, so the diagram shows the energy spent in the air.

No Streamlit here (tests/test_architecture.py).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src import theme
from src.data import schema

# group_by -> (flights column, unit shown after the value, word used in sentences)
GROUPS: dict[str, tuple[str, str, str]] = {
    "altitude": ("altitude_m", " m", "altitude"),
    "speed": ("speed_mps", " m/s", "speed"),
    "payload": ("payload_g", " g", "payload"),
    "route": ("route", "", "route"),
}

MAIN_PHASES: tuple[str, ...] = tuple(p for p in schema.PHASES if p != "Ground")
SUB_PHASES: tuple[str, ...] = tuple(s for s in schema.SUB_PHASES if s != "Ground")
# Labels on the chart; "waypoint" is written in full (docs/interfaces.md, "Writing on screen").
SUB_LABEL = {s: ("Waypoint turn" if s == "WP turn" else s) for s in SUB_PHASES}

GROUP_NODE_COLOUR = theme.PALETTES["phase"]["Ground"]  # neutral grey: a group is not a phase
# Band opacity. At 0.35 take-off and cruise bands came too close for protanopia and
# tritanopia (simulated CIELAB distance about 8 on white and on the dark theme); at 0.55 every
# pair of main-phase bands stays above 12 in both themes.
LINK_ALPHA_MAIN = 0.55
LINK_ALPHA_SUB = 0.4


# ---- data shaping --------------------------------------------------------------------------


def flights_for(flights: pd.DataFrame, group_by: str) -> pd.DataFrame:
    """The flights a grouping compares.

    Altitude, speed and payload compare only the R1 design flights, because only there are the
    three settings balanced (on R2-R5 every flight carries 0 g). Route uses every flight the
    sidebar lets through.
    """
    if group_by == "route":
        return flights
    return flights.loc[flights["in_design"].astype(bool)]


def energy_by_group(
    phase_energy: pd.DataFrame, flights: pd.DataFrame, group_by: str
) -> tuple[pd.DataFrame, pd.Series]:
    """Mean energy per flight (Wh) of every airborne sub-phase, one row per group.

    Returns the table (index = group value, sorted; columns = SUB_PHASES) and the number of
    flights in each group. ``phase_energy`` has a row for every flight and sub-phase, zeros
    included, so a sum divided by the number of flights is a true mean.
    """
    column = GROUPS[group_by][0]
    chosen = flights_for(flights, group_by)[["flight", column]].dropna(subset=[column])
    rows = phase_energy.merge(chosen, on="flight", how="inner")
    rows = rows.loc[rows["sub_phase"].isin(SUB_PHASES)]
    if rows.empty:
        return pd.DataFrame(columns=list(SUB_PHASES)), pd.Series(dtype=int)

    counts = chosen.loc[chosen["flight"].isin(rows["flight"])].groupby(column)["flight"].nunique()
    totals = rows.pivot_table(
        index=column, columns="sub_phase", values="energy_wh", aggfunc="sum", fill_value=0.0
    )
    table = totals.reindex(columns=list(SUB_PHASES), fill_value=0.0).div(counts, axis=0)
    table = table.sort_index()
    return table, counts.reindex(table.index)


def main_phase_energy(table: pd.DataFrame) -> pd.DataFrame:
    """Sum the sub-phase columns into the four main phases."""
    return pd.DataFrame(
        {
            main: table[[s for s in SUB_PHASES if schema.SUB_PHASE_PARENT[s] == main]].sum(axis=1)
            for main in MAIN_PHASES
        }
    )


def group_label(value, group_by: str, n_flights: int | None = None) -> str:
    """'25 m', '4 m/s', '250 g'; a route also shows its number of flights."""
    unit = GROUPS[group_by][1]
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = f"{value}{unit}"
    if group_by == "route" and n_flights is not None:
        text += f" ({n_flights} flight{'s' if n_flights != 1 else ''})"
    return text


# ---- figure --------------------------------------------------------------------------------


def _rgba(hex_colour: str, alpha: float) -> str:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def _stack(values: list[float], gap: float) -> list[float]:
    """Vertical centres for nodes stacked top to bottom, each as tall as its value.

    Plotly places nodes itself when no positions are given, and it often crosses bands. Fixed
    positions keep the order of groups, phases and sub-phases the same on every redraw.
    """
    total = sum(values)
    room = 1 - gap * (len(values) - 1)
    centres, y = [], 0.0
    for v in values:
        h = room * v / total if total else 0
        centres.append(min(0.999, max(0.001, y + h / 2)))
        y += h + gap
    return centres


def build_sankey(
    phase_energy: pd.DataFrame,
    flights: pd.DataFrame,
    group_by: str = "altitude",
) -> go.Figure:
    """Energy budget: group -> main phase -> sub-phase.

    A band from a group is the energy (Wh) of an average flight of that group. The bands into a
    main phase add up to the bands out of it, so the middle and right-hand nodes are sums over
    the groups; their hover text gives the mean over the groups instead.
    """
    table, counts = energy_by_group(phase_energy, flights, group_by)
    fig = go.Figure()
    if table.empty:
        fig.add_annotation(text="No flights match the filters.", showarrow=False)
        fig.update_layout(xaxis_visible=False, yaxis_visible=False, height=200)
        return fig

    mains = main_phase_energy(table)
    group_total = table.sum(axis=1)
    n_groups = len(table)
    mean_total = group_total.mean()

    flow_sub = table.sum(axis=0)  # main -> sub, summed over groups
    active_mains = [m for m in MAIN_PHASES if mains[m].sum() > 1e-9]
    active_subs = [s for s in SUB_PHASES if flow_sub[s] > 1e-9]

    def across(total_wh: float) -> str:
        mean = total_wh / n_groups
        where = "across the groups" if n_groups > 1 else "in this group"
        return (
            f"on average {mean:.2f} Wh per flight {where}<br>"
            f"({100 * mean / mean_total:.0f}% of the energy in the air)"
        )

    groups = list(table.index)
    labels = [group_label(g, group_by, int(counts[g])) for g in groups]
    labels += active_mains + [SUB_LABEL[s] for s in active_subs]
    colours = [GROUP_NODE_COLOUR] * len(groups)
    colours += [theme.PALETTES["phase"][m] for m in active_mains]
    colours += [theme.PALETTES["sub_phase"][s] for s in active_subs]
    node_hover = [
        f"{int(counts[g])} flight{'s' if int(counts[g]) != 1 else ''}<br>"
        f"{group_total[g]:.1f} Wh per flight in the air"
        for g in groups
    ]
    node_hover += [across(mains[m].sum()) for m in active_mains]
    node_hover += [across(flow_sub[s]) for s in active_subs]
    main_at = {m: len(groups) + i for i, m in enumerate(active_mains)}
    sub_at = {s: len(groups) + len(active_mains) + i for i, s in enumerate(active_subs)}

    source, target, value, link_colour, hover = [], [], [], [], []
    for i, g in enumerate(groups):
        n = int(counts[g])
        for m in active_mains:
            wh = mains.at[g, m]
            source.append(i)
            target.append(main_at[m])
            value.append(float(wh))
            link_colour.append(_rgba(theme.PALETTES["phase"][m], LINK_ALPHA_MAIN))
            hover.append(
                f"{group_label(g, group_by)} → {m}<br>{wh:.2f} Wh per flight "
                f"({100 * wh / group_total[g]:.0f}% of this group's energy)<br>"
                f"{n} flight{'s' if n != 1 else ''}"
            )
    for s in active_subs:
        m = schema.SUB_PHASE_PARENT[s]
        source.append(main_at[m])
        target.append(sub_at[s])
        value.append(float(flow_sub[s]))
        link_colour.append(_rgba(theme.PALETTES["sub_phase"][s], LINK_ALPHA_SUB))
        hover.append(f"{m} → {SUB_LABEL[s]}<br>{across(flow_sub[s])}")

    node_total = [0.0] * len(labels)
    for s0, t0, v in zip(source, target, value, strict=True):
        if s0 < len(groups):
            node_total[s0] += v
        node_total[t0] += v
    y = (
        _stack(node_total[: len(groups)], 0.04)
        + _stack([node_total[main_at[m]] for m in active_mains], 0.04)
        + _stack([node_total[sub_at[s]] for s in active_subs], 0.03)
    )
    x = [0.001] * len(groups) + [0.5] * len(active_mains) + [0.999] * len(active_subs)

    fig.add_trace(
        go.Sankey(
            arrangement="snap",
            # No fixed colour: the app theme picks a readable one in light and dark mode. Plotly
            # draws a halo around node labels by default; it smears text on a dark background.
            textfont=dict(size=13, shadow="none"),
            node=dict(
                label=labels,
                color=colours,
                x=x,
                y=y,
                pad=14,
                thickness=16,
                line=dict(width=0),
                customdata=node_hover,
                hovertemplate="<b>%{label}</b><br>%{customdata}<extra></extra>",
            ),
            link=dict(
                source=source,
                target=target,
                value=value,
                color=link_colour,
                customdata=hover,
                hovertemplate="%{customdata}<extra></extra>",
            ),
        )
    )
    # The top margin keeps the chart's toolbar (camera icon) off the top-right node label.
    fig.update_layout(height=520, margin=dict(l=10, r=10, t=40, b=10))
    return fig


# ---- finding -------------------------------------------------------------------------------


def _pct(x: float) -> str:
    return f"{x:.0f}%"


def describe_sankey(
    phase_energy: pd.DataFrame,
    flights: pd.DataFrame,
    group_by: str = "altitude",
) -> str | None:
    """One or two sentences about the groups on screen, computed from the filtered data.

    Compares the first and the last group (lowest and highest value). Each grouping reports the
    change it is known for: altitude -> take-off and landing; speed -> waypoint turns and
    straight legs; payload -> extra energy and where it goes; route -> most and least energy.
    """
    table, counts = energy_by_group(phase_energy, flights, group_by)
    if table.empty:
        return None
    mains = main_phase_energy(table)
    share = 100 * mains.div(mains.sum(axis=1), axis=0)
    sub_share = 100 * table.div(table.sum(axis=1), axis=0)

    if len(table) == 1:
        g = table.index[0]
        top = share.loc[g].idxmax()
        where = (
            f"On route {g}" if group_by == "route" else f"In the {group_label(g, group_by)} group"
        )
        return (
            f"{where}, {top.lower()} takes the largest share: {_pct(share.at[g, top])} of a "
            "flight's energy."
        )

    lo, hi = table.index[0], table.index[-1]
    lo_l, hi_l = group_label(lo, group_by), group_label(hi, group_by)

    if group_by == "altitude":
        vert = share["Take-off"] + share["Landing"]
        return (
            f"At {lo_l}, take-off and landing use {_pct(vert[lo])} of a flight's energy. "
            f"At {hi_l}, they use {_pct(vert[hi])}."
        )
    if group_by == "speed":
        turn, leg = sub_share["WP turn"], sub_share["Straight leg"]
        return (
            f"At {lo_l}, waypoint turns use {_pct(turn[lo])} of a flight's energy and straight "
            f"legs use {_pct(leg[lo])}. At {hi_l}, waypoint turns use {_pct(turn[hi])} and "
            f"straight legs use {_pct(leg[hi])}."
        )
    if group_by == "payload":
        total = mains.sum(axis=1)
        diff = mains.loc[hi] - mains.loc[lo]
        top = diff.idxmax()
        more = "more" if total[hi] >= total[lo] else "less"
        return (
            f"A flight with {hi_l} uses {total[hi]:.1f} Wh in the air, which is "
            f"{abs(total[hi] - total[lo]):.1f} Wh {more} than a flight with {lo_l}. "
            f"The largest part of the difference is in {top.lower()} ({diff[top]:.1f} Wh)."
        )
    # route
    total = mains.sum(axis=1)
    most, least = total.idxmax(), total.idxmin()
    others = counts.drop(counts.idxmax())
    lo_n, hi_n = int(others.min()), int(others.max())
    n_text = f"{lo_n}–{hi_n} flights" if hi_n > lo_n else f"{lo_n} flight{'s' if lo_n != 1 else ''}"
    few = f" Every route except {counts.idxmax()} has only {n_text}."
    return (
        f"Route {most} uses the most energy per flight ({total[most]:.1f} Wh), and route "
        f"{least} uses the least ({total[least]:.1f} Wh).{few}"
    )
