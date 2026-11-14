"""Parallel coordinates plot for flight behavioral regimes (owner: uiml)."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import plotly.graph_objects as go

from src.theme import PALETTES

PCP_AXES: tuple[tuple[str, str, str], ...] = (
    ("payload_g", "Payload (g)", ".0f"),
    ("speed_mps", "Speed (m/s)", ".0f"),
    ("altitude_m", "Altitude (m)", ".0f"),
    ("duration_s", "Duration (s)", ".0f"),
    ("energy_wh", "Energy (Wh)", ".1f"),
    ("wh_per_km", "Wh per km (Wh/km)", ".1f"),
    ("cruise_power_w", "Cruise power (W)", ".0f"),
    ("climb_power_w", "Climb power (W)", ".0f"),
    ("voltage_drop_v", "Voltage drop (V)", ".2f"),
)


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

    required_cols = [col for col, _, _ in PCP_AXES]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise KeyError(f"flights is missing required PCP columns: {missing}")

    return df.dropna(subset=required_cols + ["cluster"]).reset_index(drop=True)


def _cluster_colorscale(k: int) -> list[list[float | str]]:
    """Build a discrete Plotly colorscale for k groups using theme categorical colours."""
    colors = list(PALETTES["categorical"])[:k]
    scale: list[list[float | str]] = []
    for idx, color in enumerate(colors):
        low = idx / k
        high = (idx + 1) / k
        scale.append([low, color])
        scale.append([high, color])
    return scale


def _legend_annotation(k: int) -> dict[str, object]:
    """Build a key line annotation mapping categorical colours to Group 1..k."""
    colors = list(PALETTES["categorical"])[:k]
    items = [f'<span style="color:{colors[i]}">■</span> Group {i + 1}' for i in range(k)]
    return {
        "text": "Groups:  " + "   ".join(items),
        "x": 0.0,
        "y": 1.13,
        "xref": "paper",
        "yref": "paper",
        "xanchor": "left",
        "yanchor": "bottom",
        "showarrow": False,
        "font": {"size": 12},
    }


def build_pcp(
    flights: pd.DataFrame,
    labels: pd.Series | Sequence[str],
) -> go.Figure:
    """Build an interactive 9-measure + cluster Parallel Coordinates Plot."""
    df = _prepare_pcp_frame(flights, labels)
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title="No complete flights available for parallel coordinates")
        return fig

    cluster_codes = df["cluster"].astype(str).str.extract(r"(\d+)", expand=False).astype(int)
    k = max(int(cluster_codes.max()), 1)

    dimensions: list[dict[str, object]] = []
    for col, label, fmt in PCP_AXES:
        vals = df[col].to_numpy(dtype=float)
        lo, hi = float(vals.min()), float(vals.max())
        if lo == hi:
            tick_vals = [lo]
        else:
            step = (hi - lo) / 3.0
            tick_vals = [lo + i * step for i in range(4)]
        dimensions.append(
            {
                "label": label,
                "values": vals,
                "range": [lo, hi],
                "tickvals": tick_vals,
                "tickformat": fmt,
            }
        )

    tick_vals = list(range(1, k + 1))
    dimensions.append(
        {
            "label": "Group",
            "values": cluster_codes.to_numpy(dtype=float),
            "range": [1, k],
            "tickvals": tick_vals,
            "ticktext": [f"Group {i}" for i in tick_vals],
        }
    )

    fig = go.Figure(
        data=[
            go.Parcoords(
                line={
                    "color": cluster_codes.to_numpy(dtype=float),
                    "colorscale": _cluster_colorscale(k),
                    "cmin": 1,
                    "cmax": k,
                    "showscale": False,
                },
                dimensions=dimensions,
                unselected={"line": {"color": "rgba(180, 180, 180, 0.25)"}},
            )
        ]
    )

    fig.update_layout(
        annotations=[_legend_annotation(k)],
        margin={"l": 45, "r": 35, "t": 65, "b": 25},
        height=460,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
