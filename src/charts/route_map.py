"""Route map (G1): where the drone flew, coloured by a measure. Pure Plotly; no Streamlit.

The section draws one map per flight and places two maps side by side (chart guide: "A and B
side by side, same colour scale"), passing the same ``color_range`` to both.
"""

from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go

from src.theme import PALETTES

METRICS = {
    "Power (W)": ("power_w", "W"),
    "Ground speed (m/s)": ("ground_speed_mps", "m/s"),
    "Relative altitude (m)": ("alt_rel_m", "m"),
    "Estimated phase": ("phase", ""),
}
TRACK_COLOR = "#4f4d48"
MARKER_DARK = "#1d1c1a"


def metric_range(
    telemetry: pd.DataFrame, flight_ids: list[int], color_by: str
) -> tuple[float, float] | None:
    """Shared colour range for the selected flights, so equal colours mean equal values."""
    metric, _ = METRICS[color_by]
    if metric == "phase" or metric not in telemetry.columns:
        return None
    values = pd.to_numeric(
        _airborne(telemetry.loc[telemetry["flight"].isin(flight_ids)])[metric], errors="coerce"
    )
    if values.notna().any():
        return float(values.min()), float(values.max())
    return None


def _airborne(rows: pd.DataFrame) -> pd.DataFrame:
    """Rows in the air. Ground rows all sit on the home point and would stretch the colour
    scale down to 0 W, so they are left out of the dots (not out of the path)."""
    if "phase" in rows.columns:
        in_air = rows["phase"] != "Ground"
        if in_air.any():  # the sample tables label every row "Ground"; then keep them all
            return rows.loc[in_air]
    return rows


def _fit_zoom(lat: pd.Series, lon: pd.Series, width_px: int = 600, height_px: int = 400) -> float:
    """Web-Mercator zoom at which the track fits the map (a little margin, clamped)."""
    cos_lat = math.cos(math.radians(float(lat.mean())))
    east_m = max(float(lon.max() - lon.min()) * 111_320 * cos_lat, 20.0)
    north_m = max(float(lat.max() - lat.min()) * 110_540, 20.0)
    metres_per_pixel_at_zoom_0 = 156_543.03 * cos_lat
    zoom_x = math.log2(width_px * metres_per_pixel_at_zoom_0 / east_m)
    zoom_y = math.log2(height_px * metres_per_pixel_at_zoom_0 / north_m)
    return max(10.0, min(18.0, min(zoom_x, zoom_y) - 0.4))


def build_route_map(
    telemetry: pd.DataFrame,
    waypoints: pd.DataFrame | None,
    flight_ids: list[int],
    color_by: str = "Power (W)",
    color_range: tuple[float, float] | None = None,
    title: str | None = None,
) -> go.Figure:
    """Map of up to two flights (the section passes one) with home and waypoint markers."""
    if color_by not in METRICS:
        raise ValueError(f"Unknown map metric: {color_by}")
    metric, unit = METRICS[color_by]
    data = telemetry.loc[telemetry["flight"].isin(flight_ids[:2])].dropna(
        subset=["lat_deg", "lon_deg"]
    )
    fig = go.Figure()
    if data.empty:
        return fig.update_layout(title="No telemetry for the selected flights")
    if color_range is None:
        color_range = metric_range(data, flight_ids[:2], color_by)

    for i, (flight_id, group) in enumerate(data.groupby("flight", sort=False)):
        group = group.sort_values("t_s")
        first = i == 0
        fig.add_trace(  # the path itself, in a neutral colour under the coloured dots
            go.Scattermap(
                lat=group["lat_deg"],
                lon=group["lon_deg"],
                mode="lines",
                line={"width": 3, "color": TRACK_COLOR},
                name=f"Flight {flight_id}",
                hoverinfo="skip",
                legendgroup=f"f{flight_id}",
            )
        )
        dots = _airborne(group)
        phases = (
            dots["phase"].fillna("Unlabelled")
            if "phase" in dots
            else pd.Series("Unlabelled", index=dots.index)
        )
        text = [
            f"Flight {flight_id}<br>t = {t:.0f} s<br>Power = {p:.0f} W<br>"
            f"Ground speed = {s:.1f} m/s<br>Altitude = {a:.1f} m<br>Estimated phase = {ph}"
            for t, p, s, a, ph in zip(
                dots["t_s"],
                dots["power_w"],
                dots["ground_speed_mps"],
                dots["alt_rel_m"],
                phases,
                strict=True,
            )
        ]
        hover = pd.Series(text, index=dots.index)
        if metric == "phase":
            order = [p for p in PALETTES["phase"] if p in set(phases)]
            order += [p for p in phases.unique() if p not in order]
            for phase in order:  # legend in the same order everywhere
                subset = dots.loc[phases == phase]
                fig.add_trace(
                    go.Scattermap(
                        lat=subset["lat_deg"],
                        lon=subset["lon_deg"],
                        mode="markers",
                        marker={"size": 7, "color": PALETTES["phase"].get(phase, "#888888")},
                        text=hover.loc[subset.index].tolist(),
                        hovertemplate="%{text}<extra></extra>",
                        name=phase,
                        showlegend=first,
                        legendgroup=f"phase-{phase}",
                    )
                )
        else:
            marker = {"size": 7, "color": dots[metric], "colorscale": "Viridis"}
            if color_range is not None:
                marker.update(cmin=color_range[0], cmax=color_range[1])
            if first:
                marker.update(showscale=True, colorbar={"title": unit, "len": 0.7})
            fig.add_trace(
                go.Scattermap(
                    lat=dots["lat_deg"],
                    lon=dots["lon_deg"],
                    mode="markers",
                    marker=marker,
                    text=text,
                    hovertemplate="%{text}<extra></extra>",
                    showlegend=False,
                    legendgroup=f"f{flight_id}",
                )
            )

        # Plan markers (chart guide): a dark home marker and white-centred waypoint rings.
        start = group.iloc[0]
        fig.add_trace(
            go.Scattermap(
                lat=[start["lat_deg"]],
                lon=[start["lon_deg"]],
                mode="markers+text",
                marker={"size": 16, "color": MARKER_DARK},
                text=["H"],
                textposition="middle left",
                textfont={"size": 13, "color": MARKER_DARK},
                name="Home (take-off)",
                hovertemplate=f"Flight {flight_id} · home (take-off)<extra></extra>",
                showlegend=first,
                legendgroup="home",
            )
        )
        if waypoints is not None and not waypoints.empty:
            wp = waypoints.loc[(waypoints["flight"] == flight_id) & (waypoints["wp_index"] > 0)]
            if not wp.empty:
                labels = [f"WP{v}" for v in wp["wp_index"]]
                fig.add_trace(  # dark ring
                    go.Scattermap(
                        lat=wp["lat_deg"],
                        lon=wp["lon_deg"],
                        mode="markers",
                        marker={"size": 18, "color": MARKER_DARK},
                        hoverinfo="skip",
                        showlegend=False,
                    )
                )
                fig.add_trace(  # white centre and label
                    go.Scattermap(
                        lat=wp["lat_deg"],
                        lon=wp["lon_deg"],
                        mode="markers+text",
                        marker={"size": 11, "color": "#ffffff"},
                        text=labels,
                        textposition="top right",
                        textfont={"size": 12, "color": MARKER_DARK},
                        name="Waypoint (estimated turn)",
                        hovertext=[f"Flight {flight_id} · waypoint {w[2:]}" for w in labels],
                        hovertemplate="%{hovertext}<extra></extra>",
                        showlegend=first,
                        legendgroup="waypoints",
                    )
                )

    fig.update_layout(
        title=title or f"Flight path · {color_by}",
        map={
            "style": "carto-positron",
            "center": {
                "lat": float((data["lat_deg"].min() + data["lat_deg"].max()) / 2),
                "lon": float((data["lon_deg"].min() + data["lon_deg"].max()) / 2),
            },
            "zoom": _fit_zoom(data["lat_deg"], data["lon_deg"]),
        },
        height=460,
        legend={"orientation": "h", "y": -0.02, "yanchor": "top"},
        margin={"l": 0, "r": 0, "t": 48, "b": 0},
    )
    return fig
