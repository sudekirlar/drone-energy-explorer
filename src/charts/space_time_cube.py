"""Three-dimensional geographic trajectories against elapsed time or altitude (G2)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.data import schema
from src.theme import PALETTES

COLOR_COLUMNS = {"Power (W)": "power_w", "Relative altitude (m)": "alt_rel_m"}


def _flight_rows(data: pd.DataFrame, flight: int, from_takeoff: bool) -> pd.DataFrame:
    """The airborne rows of one flight, in time order."""
    group = data.loc[data["flight"] == flight].sort_values("t_s")
    if from_takeoff:
        group = group.loc[group["t_since_takeoff_s"] >= 0]
    if "phase" in group.columns:
        airborne = group["phase"] != "Ground"
        if airborne.any():  # sample tables label every row "Ground"; keep them visible
            group = group.loc[airborne]
    return group


def build_space_time_cube(
    telemetry: pd.DataFrame,
    flight_ids: list[int],
    z_axis: str = "Time (s)",
    color_by: str = "Flight",
) -> go.Figure:
    """Render up to four selected flights in local east/north coordinates."""
    if z_axis not in ("Time (s)", "Relative altitude (m)"):
        raise ValueError("Unknown vertical axis")
    if color_by not in ("Flight", "Power (W)", "Relative altitude (m)", "Estimated phase"):
        raise ValueError("Unknown colour metric")

    fig = go.Figure()
    data = telemetry.loc[telemetry["flight"].isin(flight_ids[:4])]
    # D2: time is counted from take-off, so every flight starts at the same height of the cube
    # and the ground waiting before and after the flight is left out.
    from_takeoff = "t_since_takeoff_s" in data.columns
    time_col = "t_since_takeoff_s" if from_takeoff else "t_s"
    zcol = time_col if z_axis == "Time (s)" else "alt_rel_m"
    z_title = "Time since take-off (s)" if from_takeoff else "Time from recording start (s)"
    groups = {f: _flight_rows(data, f, from_takeoff) for f in flight_ids[:4]}
    groups = {f: g for f, g in groups.items() if not g.empty}

    # One colour range for all flights, so the same colour means the same value in every line.
    scale = None
    if color_by in COLOR_COLUMNS and groups:
        values = pd.concat([g[COLOR_COLUMNS[color_by]] for g in groups.values()])
        scale = (float(values.min()), float(values.max()))

    phases_in_legend: set[str] = set()
    for i, (flight, group) in enumerate(groups.items()):
        line_color = PALETTES["categorical"][i % len(PALETTES["categorical"])]
        fig.add_trace(
            go.Scatter3d(
                x=group["east_m"],
                y=group["north_m"],
                z=group[zcol],
                mode="lines",
                line={"color": line_color, "width": 5},
                name=f"Flight {flight}",
                legendgroup="flights",
                legendrank=i + 1,
                customdata=group[[time_col, "power_w", "alt_rel_m"]].to_numpy(),
                hovertemplate="East=%{x:.1f} m<br>North=%{y:.1f} m<br>"
                "Time=%{customdata[0]:.0f} s<br>Power=%{customdata[1]:.1f} W<br>"
                "Alt=%{customdata[2]:.1f} m<extra>%{fullData.name}</extra>",
            )
        )
        if color_by == "Estimated phase" and "phase" in group.columns:
            # One trace per phase, so every phase colour has a legend entry. Clicking an entry
            # hides that phase in all flights at once.
            for rank, phase in enumerate(schema.PHASES):
                rows = group.loc[group["phase"] == phase]
                if rows.empty:
                    continue
                fig.add_trace(
                    go.Scatter3d(
                        x=rows["east_m"],
                        y=rows["north_m"],
                        z=rows[zcol],
                        mode="markers",
                        marker={"size": 2, "color": PALETTES["phase"][phase]},
                        name=phase,
                        legendgroup=f"phase-{phase}",
                        legendrank=100 + rank,
                        showlegend=phase not in phases_in_legend,
                        hoverinfo="skip",
                    )
                )
                phases_in_legend.add(phase)
        elif scale is not None:
            fig.add_trace(
                go.Scatter3d(
                    x=group["east_m"],
                    y=group["north_m"],
                    z=group[zcol],
                    mode="markers",
                    marker={
                        "size": 2,
                        "color": group[COLOR_COLUMNS[color_by]],
                        "colorscale": "Viridis",
                        "cmin": scale[0],
                        "cmax": scale[1],
                        "showscale": i == 0,
                        "colorbar": {"title": {"text": color_by}, "len": 0.6, "x": 1.0},
                    },
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
    fig.update_layout(
        title="Space–Time Cube • flight trajectories",
        height=600,
        scene={
            "xaxis_title": "East (m)",
            "yaxis_title": "North (m)",
            "zaxis_title": z_title if z_axis == "Time (s)" else z_axis,
            # Same view as the chart guide: the triangle seen from the south-east, a tall z axis.
            "camera": {"eye": {"x": 1.7, "y": -1.6, "z": 0.8}},
            "aspectmode": "manual",
            "aspectratio": {"x": 1, "y": 1.4, "z": 1.6 if z_axis == "Time (s)" else 0.9},
        },
        # The legend sits under the cube, so it never covers the colour bar on the right.
        legend={"orientation": "h", "yanchor": "top", "y": -0.02, "xanchor": "left", "x": 0},
        margin={"l": 0, "r": 0, "t": 55, "b": 40},
    )
    return fig
