"""Parallel coordinates plot for flight behavioral regimes (owner: uiml)."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import plotly.graph_objects as go

from src import theme

CLUSTER_PALETTE: tuple[str, ...] = (
    "#0072B2",  # G1 - Blue (lowest energy)
    "#009E73",  # G2 - Bluish green
    "#E69F00",  # G3 - Orange
    "#CC79A7",  # G4 - Reddish purple
    "#56B4E9",  # G5 - Sky blue
    "#D55E00",  # G6 - Vermilion
)

PCP_AXES: tuple[tuple[str, str], ...] = (
    ("payload_g", "Payload (g)"),
    ("speed_mps", "Speed (m/s)"),
    ("altitude_m", "Altitude (m)"),
    ("duration_s", "Duration (s)"),
    ("energy_wh", "Energy (Wh)"),
    ("wh_per_km", "Wh per km (Wh/km)"),
    ("cruise_power_w", "Cruise power (W)"),
    ("climb_power_w", "Climb power (W)"),
    ("voltage_drop_v", "Voltage drop (V)"),
)


def _get_categorical_colors() -> list[str]:
    for attr in ("PALETTE", "PALETTES", "COLORS", "COLOR_PALETTE"):
        obj = getattr(theme, attr, None)
        if isinstance(obj, dict) and "categorical" in obj:
            return list(obj["categorical"])
    return list(CLUSTER_PALETTE)


def _prepare_pcp_frame(flights: pd.DataFrame, labels: pd.Series | Sequence[str]) -> pd.DataFrame:
    """Align flights and cluster labels, deriving voltage drop if needed."""
    df = flights.copy().reset_index(drop=True)
    df["cluster"] = pd.Series(labels, index=df.index, name="cluster")

    if "voltage_drop_v" not in df.columns:
        if {"start_voltage_v", "end_voltage_v"}.issubset(df.columns):
            df["voltage_drop_v"] = df["start_voltage_v"] - df["end_voltage_v"]
        else:
            raise KeyError(
                "flights must contain 'voltage_drop_v' or "
                "both 'start_voltage_v' and 'end_voltage_v'."
            )

    required_cols = [col for col, _ in PCP_AXES]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise KeyError(f"flights is missing required PCP columns: {missing}")

    return df.dropna(subset=required_cols + ["cluster"]).reset_index(drop=True)


def _cluster_colorscale(max_k: int = 6) -> list[list[float | str]]:
    """Build a discrete Plotly colorscale anchored to G1..G6."""
    colors = _get_categorical_colors()
    while len(colors) < max_k:
        colors.extend(CLUSTER_PALETTE)
    colors = colors[:max_k]

    scale: list[list[float | str]] = []
    for idx, color in enumerate(colors):
        low = idx / max_k
        high = (idx + 1) / max_k
        scale.append([low, color])
        scale.append([high, color])
    return scale


def build_pcp(
    flights: pd.DataFrame,
    labels: pd.Series | Sequence[str],
    max_k: int = 6,
) -> go.Figure:
    """Build an interactive 9-measure + cluster Parallel Coordinates Plot."""
    df = _prepare_pcp_frame(flights, labels)
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title="No complete flights available for parallel coordinates")
        return fig

    cluster_codes = df["cluster"].astype(str).str.extract(r"(\d+)", expand=False).astype(int)

    dimensions: list[dict[str, object]] = [
        {"label": label, "values": df[col].to_numpy(dtype=float)} for col, label in PCP_AXES
    ]

    tick_vals = list(range(1, max_k + 1))
    dimensions.append(
        {
            "label": "Cluster",
            "values": cluster_codes.to_numpy(dtype=float),
            "range": [1, max_k],
            "tickvals": tick_vals,
            "ticktext": [f"G{i}" for i in tick_vals],
        }
    )

    fig = go.Figure(
        data=[
            go.Parcoords(
                line={
                    "color": cluster_codes.to_numpy(dtype=float),
                    "colorscale": _cluster_colorscale(max_k=max_k),
                    "cmin": 1,
                    "cmax": max_k,
                    "showscale": False,
                },
                dimensions=dimensions,
                unselected={"line": {"color": "rgba(180, 180, 180, 0.25)"}},
            )
        ]
    )

    fig.update_layout(
        margin={"l": 45, "r": 35, "t": 45, "b": 25},
        height=460,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
