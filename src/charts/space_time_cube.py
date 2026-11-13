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
    zcol = "t_s" if z_axis == "Time (s)" else "alt_rel_m"
    for i, flight in enumerate(flights):
        group = data.loc[data["flight"] == flight].sort_values("t_s")
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
                customdata=group[["t_s", "power_w", "alt_rel_m"]].to_numpy(),
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
            "zaxis_title": z_axis,
            "camera": {"eye": {"x": 1.65, "y": 1.45, "z": 1.2}},
        },
        margin={"l": 0, "r": 0, "t": 55, "b": 0},
    )
    return fig
