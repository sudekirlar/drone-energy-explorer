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
    fig = px.box(
        plot_df,
        x="payload_label",
        y="energy_wh",
        color="payload_label",
        color_discrete_sequence=PALETTES["categorical"],
        labels={"payload_label": "Payload (g)", "energy_wh": "Total Energy (Wh)"},
        title="Heavier payloads shift total flight energy upward",
    )
    fig.update_layout(showlegend=False)
    return (
        fig,
        "Median total energy increases steadily as payload mass grows from 0 g to 500 g.",
    )


def _build_energy_by_route(tables: dict[str, pd.DataFrame]) -> tuple[go.Figure, str]:
    flights = tables["flights"]
    summary = flights.groupby("route", as_index=False)["energy_wh"].mean().sort_values("route")
    fig = px.bar(
        summary,
        x="route",
        y="energy_wh",
        color="route",
        color_discrete_sequence=PALETTES["categorical"],
        labels={"route": "Route", "energy_wh": "Mean Energy (Wh)"},
        title="Mean total energy varies substantially across routes R1–R7",
    )
    fig.update_layout(showlegend=False)
    return (
        fig,
        "Route geometry and mission length drive distinct baseline energy budgets.",
    )


def render(tables: dict[str, pd.DataFrame]) -> None:
    """Render Overview KPIs and the T4 example card."""
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
        title="Payload and route strongly shape flight energy budgets",
        how_to_read=(
            "Compare median and spread of total energy (Wh) across payload or route groups."
        ),
        tables=tables,
        options={
            "Total Energy by Payload": _build_energy_by_payload,
            "Mean Energy by Route": _build_energy_by_route,
        },
        key_prefix="overview_example",
    )