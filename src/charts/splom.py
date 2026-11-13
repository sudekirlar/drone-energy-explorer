"""Scatterplot matrix (SPLOM) for pairwise flight telemetry relations (owner: uiml)."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import plotly.graph_objects as go

from src.theme import PALETTES

SPLOM_AXES: tuple[tuple[str, str], ...] = (
    ("speed_mps", "Speed (m/s)"),
    ("cruise_power_w", "Cruise power (W)"),
    ("climb_power_w", "Climb power (W)"),
    ("wh_per_km", "Wh per km (Wh/km)"),
    ("voltage_drop_v", "Voltage drop (V)"),
)

ALTITUDE_COLOR_MAP: dict[int, str] = {
    25: PALETTES["viridis"][0],
    50: PALETTES["viridis"][1],
    75: PALETTES["viridis"][2],
    100: PALETTES["viridis"][3],
    125: PALETTES["viridis"][4],
    150: PALETTES["viridis"][5],
}


def _color_for_payload(payload_g: int) -> str:
    payload_palette = PALETTES["payload"]
    if payload_g in payload_palette:
        return payload_palette[payload_g]
    keys = sorted(payload_palette.keys())
    return payload_palette[keys[payload_g % len(keys)]]


def _color_for_altitude(altitude_m: int) -> str:
    if altitude_m in ALTITUDE_COLOR_MAP:
        return ALTITUDE_COLOR_MAP[altitude_m]
    viridis = PALETTES["viridis"]
    idx = min(max(int(round(altitude_m / 25.0)) - 1, 0), len(viridis) - 1)
    return viridis[idx]


def _color_for_cluster(label: str) -> str:
    categorical = PALETTES["categorical"]
    digits = "".join(ch for ch in str(label) if ch.isdigit())
    idx = (int(digits) - 1) if digits else 0
    return categorical[idx % len(categorical)]


def _prepare_splom_frame(
    flights: pd.DataFrame,
    color_by: str,
    labels: pd.Series | Sequence[str] | None = None,
) -> tuple[pd.DataFrame, str, list[tuple[int, str, str]]]:
    """Validate required columns, derive voltage drop, and resolve value-mapped colours."""
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
        df = df.dropna(subset=required + ["payload_g"]).reset_index(drop=True)
        df["_group_key"] = df["payload_g"].astype(int)
        unique_keys = sorted(df["_group_key"].unique().tolist())
        groups = [(k, f"{k} g", _color_for_payload(int(k))) for k in unique_keys]
        legend_title = "Payload (g)"
    elif mode in {"altitude", "altitude_m"}:
        if "altitude_m" not in df.columns:
            raise KeyError("flights must contain 'altitude_m' when color_by='altitude'.")
        df = df.dropna(subset=required + ["altitude_m"]).reset_index(drop=True)
        df["_group_key"] = df["altitude_m"].round().astype(int)
        unique_keys = sorted(df["_group_key"].unique().tolist())
        groups = [(k, f"{k} m", _color_for_altitude(int(k))) for k in unique_keys]
        legend_title = "Altitude (m)"
    elif mode in {"cluster", "kmeans", "k-means"}:
        if labels is not None:
            df["_raw_cluster"] = pd.Series(labels, index=df.index).astype(str)
        elif "cluster" in df.columns:
            df["_raw_cluster"] = df["cluster"].astype(str)
        else:
            raise KeyError(
                "labels must be provided (or 'cluster' column present) when color_by='cluster'."
            )
        df = df.dropna(subset=required).reset_index(drop=True)
        df = df[df["_raw_cluster"].notna() & (df["_raw_cluster"] != "nan")].reset_index(drop=True)
        df["_group_key"] = df["_raw_cluster"].str.extract(r"(\d+)", expand=False).astype(int)
        unique_keys = sorted(df["_group_key"].unique().tolist())
        groups = [(k, f"Group {k}", _color_for_cluster(f"G{k}")) for k in unique_keys]
        legend_title = "K-means group"
    else:
        raise ValueError(
            f"Unsupported color_by={color_by!r}. Expected 'payload', 'cluster', or 'altitude'."
        )

    return df, legend_title, groups


def build_splom(
    flights: pd.DataFrame,
    color_by: str = "payload",
    labels: pd.Series | Sequence[str] | None = None,
) -> go.Figure:
    """Build a 5-variable lower-triangle SPLOM with linked box selection."""
    df, legend_title, groups = _prepare_splom_frame(flights, color_by=color_by, labels=labels)
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title="No complete flights available for scatterplot matrix")
        return fig

    fig = go.Figure()
    for key_val, display_name, color in groups:
        sub = df[df["_group_key"] == key_val]
        dimensions = [
            {"label": label, "values": sub[col].to_numpy(dtype=float)} for col, label in SPLOM_AXES
        ]
        hover_text = (
            [f"Flight {int(f)} · {display_name}" for f in sub["flight"]]
            if "flight" in sub.columns
            else [display_name] * len(sub)
        )
        fig.add_trace(
            go.Splom(
                name=display_name,
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
