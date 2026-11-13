"""Overview & Data Quality section (owner: Data, T4 scaffold by UI & ML)."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.sections.common import render_example_card
from src.theme import PALETTES


def _build_energy_by_payload(tables: dict[str, pd.DataFrame]) -> tuple[go.Figure, str]:
    flights = tables["flights"]
    plot_df = flights.copy()
    plot_df["payload_label"] = plot_df["payload_g"].astype(str) + " g"
    order = [f"{p} g" for p in sorted(flights["payload_g"].dropna().unique())]
    color_map = {f"{k} g": v for k, v in PALETTES["payload"].items()}

    fig = px.box(
        plot_df,
        x="payload_label",
        y="energy_wh",
        color="payload_label",
        category_orders={"payload_label": order},
        color_discrete_map=color_map,
        labels={"payload_label": "Payload (g)", "energy_wh": "Total Energy (Wh)"},
        title="Total flight energy (Wh) across payload groups",
    )
    fig.update_layout(showlegend=False)

    medians = flights.groupby("payload_g")["energy_wh"].median().sort_index()
    if len(medians) >= 2:
        low_p, high_p = medians.index[0], medians.index[-1]
        finding = (
            f"Filtered median energy shifts from {medians.iloc[0]:.1f} Wh at {low_p} g "
            f"to {medians.iloc[-1]:.1f} Wh at {high_p} g."
        )
    elif len(medians) == 1:
        only_p = medians.index[0]
        finding = f"Filtered median energy for {only_p} g payload is {medians.iloc[0]:.1f} Wh."
    else:
        finding = "No flights available in the current filter selection."

    return fig, finding


def _build_wh_per_km_by_speed(tables: dict[str, pd.DataFrame]) -> tuple[go.Figure, str]:
    flights = tables["flights"]
    plot_df = flights.copy()
    plot_df["speed_label"] = plot_df["speed_mps"].astype(str) + " m/s"
    order = [f"{s} m/s" for s in sorted(flights["speed_mps"].dropna().unique())]

    fig = px.box(
        plot_df,
        x="speed_label",
        y="wh_per_km",
        color="speed_label",
        category_orders={"speed_label": order},
        color_discrete_sequence=PALETTES["viridis"],
        labels={"speed_label": "Target Speed (m/s)", "wh_per_km": "Energy per km (Wh/km)"},
        title="Energy per kilometre (Wh/km) across target speeds",
    )
    fig.update_layout(showlegend=False)

    medians = flights.groupby("speed_mps")["wh_per_km"].median().sort_values()
    if not medians.empty:
        best_s = medians.index[0]
        finding = (
            f"Lowest median energy intensity in the current selection is {medians.iloc[0]:.1f} "
            f"Wh/km at {best_s} m/s."
        )
    else:
        finding = "No flights available in the current filter selection."

    return fig, finding


def render(tables: dict[str, pd.DataFrame]) -> None:
    """Render Overview KPIs and the single T4 contract example card."""
    flights = tables["flights"]
    st.markdown("### Overview & Data Quality")

    n_flights = int(flights["flight"].nunique())
    mean_energy = float(flights["energy_wh"].mean()) if len(flights) else 0.0
    mean_power = float(flights["mean_power_w"].mean()) if len(flights) else 0.0
    outlier_count = int(flights["is_outlier"].sum()) if len(flights) else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Filtered Flights", f"{n_flights:,}")
    col2.metric("Mean Energy (Wh)", f"{mean_energy:.1f}")
    col3.metric("Mean Power (W)", f"{mean_power:.1f}")
    col4.metric("Flagged Outliers", f"{outlier_count:,}")

    render_example_card(
        title="Energy consumption across experimental conditions",
        how_to_read=(
            "Each box shows the median, interquartile range, and spread across filtered flights."
        ),
        tables=tables,
        options={
            "Total Energy (Wh) by Payload": _build_energy_by_payload,
            "Energy per km (Wh/km) by Speed": _build_wh_per_km_by_speed,
        },
        key_prefix="overview_example",
    )
