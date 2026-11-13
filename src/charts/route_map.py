"""Interactive geographic drone flight map (G1). Pure Plotly; no Streamlit."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.theme import PALETTES

METRICS = {
    "Power (W)": ("power_w", "W"),
    "Ground speed (m/s)": ("ground_speed_mps", "m/s"),
    "Relative altitude (m)": ("alt_rel_m", "m"),
    "Estimated phase": ("phase", ""),
}


def build_route_map(
    telemetry: pd.DataFrame,
    waypoints: pd.DataFrame | None,
    flight_ids: list[int],
    color_by: str = "Power (W)",
) -> go.Figure:
    """Show at most two flight tracks and optional Platform-supplied waypoints."""
    if color_by not in METRICS:
        raise ValueError(f"Unknown map metric: {color_by}")
    metric, unit = METRICS[color_by]
    data = telemetry.loc[telemetry["flight"].isin(flight_ids[:2])]
    fig = go.Figure()
    if data.empty:
        return fig.update_layout(title="No telemetry for the selected flights")

    numeric_range = None
    if metric != "phase":
        vals = pd.to_numeric(data[metric], errors="coerce")
        if vals.notna().any():
            numeric_range = (float(vals.min()), float(vals.max()))

    for i, (flight_id, group) in enumerate(data.groupby("flight", sort=False)):
        group = group.sort_values("t_s").dropna(subset=["lat_deg", "lon_deg"])
        if group.empty:
            continue
        color = PALETTES["categorical"][i % len(PALETTES["categorical"])]
        # Track line is a flight identifier; dots separately encode the selected quantity.
        fig.add_trace(
            go.Scattermap(
                lat=group["lat_deg"],
                lon=group["lon_deg"],
                mode="lines",
                line={"width": 4, "color": color},
                name=f"Flight {flight_id}",
                hoverinfo="skip",
                legendgroup=f"f{flight_id}",
            )
        )
        labels = (
            group["phase"].fillna("Unlabelled")
            if "phase" in group
            else pd.Series(["Unlabelled"] * len(group), index=group.index)
        )
        text = [
            f"Flight {flight_id}<br>t={t:.0f} s<br>Power={p:.1f} W<br>Speed={s:.1f} m/s"
            f"<br>Altitude={a:.1f} m<br>Phase={phase}"
            for t, p, s, a, phase in zip(
                group["t_s"],
                group["power_w"],
                group["ground_speed_mps"],
                group["alt_rel_m"],
                labels,
                strict=True,
            )
        ]
        if metric == "phase":
            for phase in labels.unique():
                subset = group.loc[labels == phase]
                ix = labels.index[labels == phase]
                fig.add_trace(
                    go.Scattermap(
                        lat=subset["lat_deg"],
                        lon=subset["lon_deg"],
                        mode="markers",
                        marker={"size": 6, "color": PALETTES["phase"].get(phase, "#888888")},
                        text=[text[group.index.get_loc(j)] for j in ix],
                        hovertemplate="%{text}<extra></extra>",
                        showlegend=False,
                        legendgroup=f"f{flight_id}",
                    )
                )
        else:
            marker = {"size": 7, "color": group[metric], "colorscale": "Viridis"}
            if numeric_range is not None:
                marker.update(cmin=numeric_range[0], cmax=numeric_range[1])
            # Only one shared colorbar, even when A and B are compared.
            if i == 0:
                marker.update(showscale=True, colorbar={"title": f"{unit}", "len": 0.65})
            fig.add_trace(
                go.Scattermap(
                    lat=group["lat_deg"],
                    lon=group["lon_deg"],
                    mode="markers",
                    marker=marker,
                    text=text,
                    hovertemplate="%{text}<extra></extra>",
                    showlegend=False,
                    legendgroup=f"f{flight_id}",
                )
            )

        start = group.iloc[0]
        fig.add_trace(
            go.Scattermap(
                lat=[start["lat_deg"]],
                lon=[start["lon_deg"]],
                mode="markers+text",
                marker={"size": 13, "color": color},
                text=["H"],
                textposition="top center",
                name=f"Home {flight_id}",
                hovertemplate=f"Flight {flight_id} start<extra></extra>",
                showlegend=False,
            )
        )
        if waypoints is not None and not waypoints.empty:
            wp = waypoints.loc[(waypoints["flight"] == flight_id) & (waypoints["wp_index"] > 0)]
            if not wp.empty:
                fig.add_trace(
                    go.Scattermap(
                        lat=wp["lat_deg"],
                        lon=wp["lon_deg"],
                        mode="markers+text",
                        marker={"size": 12, "color": color},
                        text=[f"WP{v}" for v in wp["wp_index"]],
                        textposition="top right",
                        name=f"Waypoints {flight_id}",
                        showlegend=False,
                    )
                )

    fig.update_layout(
        title=f"Flight paths • {color_by}",
        map={
            "style": "carto-positron",
            "center": {
                "lat": float(data["lat_deg"].median()),
                "lon": float(data["lon_deg"].median()),
            },
            "zoom": 15,
        },
        height=540,
        legend={"orientation": "h"},
        margin={"t": 55, "b": 12},
    )
    return fig
