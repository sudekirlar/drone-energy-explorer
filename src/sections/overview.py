"""Overview section for Drone Delivery Energy Explorer."""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data.filters import FilterState
from src.sections.common import render_example_card
from src.theme import PALETTES


def render(df: pd.DataFrame, filters: FilterState) -> None:
    """Render Overview KPIs and summary card."""
    st.markdown("### Overview")

    total_flights = df["flight"].nunique() if "flight" in df.columns else len(df)
    avg_energy = df["total_energy_wh"].mean() if "total_energy_wh" in df.columns else 0.0
    avg_power = df["mean_power_w"].mean() if "mean_power_w" in df.columns else 0.0
    avg_speed = df["target_speed"].mean() if "target_speed" in df.columns else 0.0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Filtered Flights", f"{total_flights:,}")
    col2.metric("Mean Energy (Wh)", f"{avg_energy:.1f}")
    col3.metric("Mean Power (W)", f"{avg_power:.1f}")
    col4.metric("Mean Target Speed (m/s)", f"{avg_speed:.1f}")

    def chart_by_payload(data: pd.DataFrame):
        payload_col = "payload_g" if "payload_g" in data.columns else "payload"
        fig = px.box(
            data,
            x=payload_col,
            y="total_energy_wh",
            color=payload_col,
            color_discrete_sequence=PALETTES["categorical"],
            labels={payload_col: "Payload (g)", "total_energy_wh": "Total Energy (Wh)"},
            title="Total Energy Distribution by Payload",
        )
        return (
            fig,
            "Higher payload mass consistently shifts median total energy consumption upward.",
        )

    def chart_by_route(data: pd.DataFrame):
        fig = px.bar(
            data.groupby("route", as_index=False)["total_energy_wh"].mean(),
            x="route",
            y="total_energy_wh",
            color="route",
            color_discrete_sequence=PALETTES["categorical"],
            labels={"route": "Route", "total_energy_wh": "Mean Energy (Wh)"},
            title="Mean Energy Consumption by Route",
        )
        return (
            fig,
            "Route variations reflect differences in trajectory length and maneuver profiles.",
        )

    render_example_card(
        title="Energy Summary Explorer",
        df=df,
        options={
            "Energy by Payload": chart_by_payload,
            "Mean Energy by Route": chart_by_route,
        },
        key_prefix="overview_card",
    )