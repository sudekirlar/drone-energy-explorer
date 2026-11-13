"""Scatterplot matrix (SPLOM) for pairwise flight telemetry relations (owner: uiml)."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import plotly.graph_objects as go

from src import theme

SPLOM_AXES: tuple[tuple[str, str], ...] = (
    ("speed_mps", "Speed (m/s)"),
    ("cruise_power_w", "Cruise power (W)"),
    ("climb_power_w", "Climb power (W)"),
    ("wh_per_km", "Wh per km (Wh/km)"),
    ("voltage_drop_v", "Voltage drop (V)"),
)

DEFAULT_DISCRETE_COLORS: tuple[str, ...] = (
    "#0072B2",
    "#009E73",
    "#E69F00",
    "#CC79A7",
    "#56B4E9",
    "#D55E00",
)


def _get_palette(key: str, fallback: Sequence[str]) -> list[str]:
    for attr in ("PALETTE", "PALETTES", "COLORS", "COLOR_PALETTE"):
        obj = getattr(theme, attr, None)
        if isinstance(obj, dict) and key in obj:
            val = obj[key]
            if isinstance(val, dict):
                return list(val.values())
            return list(val)
    return list(fallback)


def _prepare_splom_frame(
    flights: pd.DataFrame,
    color_by: str,
    labels: pd.Series | Sequence[str] | None = None,
) -> tuple[pd.DataFrame, str]:
    """Validate required columns, derive voltage drop, and resolve color grouping."""
    df = flights.copy().reset_index(drop=True)

    if "voltage_drop_v" not in df.columns:
        if {"start_voltage_v", "end_voltage_v"}.issubset(df.columns):
            df["voltage_drop_v"] = df["start_voltage_v"] - df["end_voltage_v"]
        else:
            raise KeyError(
                "flights must contain 'voltage_drop_v' or "
                "both 'start_voltage_v' and 'end_voltage_v'."
            )

    required = [col for col, _ in SPLOM_AXES]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise KeyError(f"flights is missing required SPLOM columns: {missing}")

    mode = color_by.strip().lower()
    if mode in {"payload", "payload_g"}:
        if "payload_g" not in df.columns:
            raise KeyError("flights must contain 'payload_g' when color_by='payload'.")
        df["_color_group"] = df["payload_g"].map(lambda v: f"{int(v)} g" if pd.notna(v) else "NA")
        legend_title = "Payload (g)"
    elif mode in {"altitude", "altitude_m"}:
        if "altitude_m" not in df.columns:
            raise KeyError("flights must contain 'altitude_m' when color_by='altitude'.")
        df["_color_group"] = df["altitude_m"].map(
            lambda v: f"{int(round(float(v)))} m" if pd.notna(v) else "NA"
        )
        legend_title = "Altitude (m)"
    elif mode in {"cluster", "kmeans", "k-means"}:
        if labels is not None:
            df["_color_group"] = pd.Series(labels, index=df.index).astype(str)
        elif "cluster" in df.columns:
            df["_color_group"] = df["cluster"].astype(str)
        else:
            raise KeyError(
                "labels must be provided (or 'cluster' column present) when color_by='cluster'."
            )
        legend_title = "K-means cluster"
    else:
        raise ValueError(
            f"Unsupported color_by={color_by!r}. Expected 'payload', 'cluster', or 'altitude'."
        )

    keep_cols = required + ["_color_group"]
    if "flight" in df.columns:
        keep_cols.append("flight")
    df = df.dropna(subset=required).reset_index(drop=True)
    df = df[df["_color_group"].notna() & (df["_color_group"] != "nan")].reset_index(drop=True)
    return df, legend_title


def _ordered_groups(series: pd.Series, mode: str) -> list[str]:
    unique_vals = [str(v) for v in series.dropna().unique()]
    if mode in {"payload", "payload_g", "altitude", "altitude_m"}:
        return sorted(
            unique_vals,
            key=lambda s: (
                float(s.split()[0]) if s.split()[0].replace(".", "", 1).isdigit() else 0.0
            ),
        )
    return sorted(unique_vals)


def build_splom(
    flights: pd.DataFrame,
    color_by: str = "payload",
    labels: pd.Series | Sequence[str] | None = None,
) -> go.Figure:
    """Build a 5-variable lower-triangle SPLOM with linked box selection."""
    df, legend_title = _prepare_splom_frame(flights, color_by=color_by, labels=labels)
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title="No complete flights available for scatterplot matrix")
        return fig

    mode = color_by.strip().lower()
    groups = _ordered_groups(df["_color_group"], mode=mode)
    palette_key = "payload" if mode in {"payload", "payload_g"} else "categorical"
    colors = _get_palette(palette_key, DEFAULT_DISCRETE_COLORS)

    fig = go.Figure()
    for idx, group_val in enumerate(groups):
        sub = df[df["_color_group"] == group_val]
        color = colors[idx % len(colors)]
        dimensions = [
            {"label": label, "values": sub[col].to_numpy(dtype=float)} for col, label in SPLOM_AXES
        ]
        hover_text = (
            [f"Flight {int(f)} · {group_val}" for f in sub["flight"]]
            if "flight" in sub.columns
            else [group_val] * len(sub)
        )
        fig.add_trace(
            go.Splom(
                name=group_val,
                dimensions=dimensions,
                text=hover_text,
                showupperhalf=False,
                diagonal_visible=False,
                marker={
                    "color": color,
                    "size": 6,
                    "opacity": 0.8,
                    "line": {"width": 0.4, "color": "white"},
                },
                selected={"marker": {"opacity": 1.0, "size": 7}},
                unselected={"marker": {"opacity": 0.18}},
            )
        )

    fig.update_layout(
        dragmode="select",
        hovermode="closest",
        legend={"title": {"text": legend_title}, "orientation": "h", "y": 1.04, "x": 0.0},
        margin={"l": 65, "r": 25, "t": 55, "b": 45},
        height=640,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
