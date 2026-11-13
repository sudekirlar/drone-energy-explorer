"""Three-dimensional geographic trajectories against elapsed time or altitude (G2)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.theme import PALETTES


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
    flights = flight_ids[:4]
    data = telemetry.loc[telemetry["flight"].isin(flights)]
    # D2: time is counted from take-off, so every flight starts at the same height of the cube
    # and the ground waiting before and after the flight is left out.
    from_takeoff = "t_since_takeoff_s" in data.columns
    time_col = "t_since_takeoff_s" if from_takeoff else "t_s"
    zcol = time_col if z_axis == "Time (s)" else "alt_rel_m"
    z_title = "Time since take-off (s)" if from_takeoff else "Time from recording start (s)"
    for i, flight in enumerate(flights):
        group = data.loc[data["flight"] == flight].sort_values("t_s")
        if from_takeoff:
            group = group.loc[group["t_since_takeoff_s"] >= 0]
        if "phase" in group.columns:
            airborne = group["phase"] != "Ground"
            if airborne.any():  # sample tables label every row "Ground"; keep them visible
                group = group.loc[airborne]
        if group.empty:
            continue
        name = f"Flight {flight}"
        base_color = PALETTES["categorical"][i % len(PALETTES["categorical"])]
        fig.add_trace(
            go.Scatter3d(
                x=group["east_m"],
                y=group["north_m"],
                z=group[zcol],
                mode="lines",
                line={"color": base_color, "width": 5},
                name=name,
                customdata=group[[time_col, "power_w", "alt_rel_m"]].to_numpy(),
                hovertemplate="East=%{x:.1f} m<br>North=%{y:.1f} m<br>"
                "Time=%{customdata[0]:.0f} s<br>Power=%{customdata[1]:.1f} W<br>"
                "Alt=%{customdata[2]:.1f} m<extra>%{fullData.name}</extra>",
            )
        )
        if color_by != "Flight":
            colorcol = "power_w" if color_by == "Power (W)" else "alt_rel_m"
            if color_by == "Estimated phase":
                labels = group["phase"].fillna("Unlabelled") if "phase" in group else []
                colors = [PALETTES["phase"].get(v, "#888888") for v in labels]
                marker = {"size": 2, "color": colors}
            else:
                marker = {"size": 2, "color": group[colorcol], "colorscale": "Viridis"}
            fig.add_trace(
                go.Scatter3d(
                    x=group["east_m"],
                    y=group["north_m"],
                    z=group[zcol],
                    mode="markers",
                    marker=marker,
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
    fig.update_layout(
        title="Space–Time Cube • flight trajectories",
        height=570,
        scene={
            "xaxis_title": "East (m)",
            "yaxis_title": "North (m)",
            "zaxis_title": z_title if z_axis == "Time (s)" else z_axis,
            # Same view as the chart guide: the triangle seen from the south-east, a tall z axis.
            "camera": {"eye": {"x": 1.7, "y": -1.6, "z": 0.8}},
            "aspectmode": "manual",
            "aspectratio": {"x": 1, "y": 1.4, "z": 1.6 if z_axis == "Time (s)" else 0.9},
        },
        margin={"l": 0, "r": 0, "t": 55, "b": 0},
    )
    return fig
