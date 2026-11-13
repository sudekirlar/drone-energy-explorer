"""Multivariate and ML section (owner: uiml)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.charts.flight_heatmap import (
    build_flight_time_heatmap,
    summarize_climb_band_by_altitude,
)
from src.sections.common import CardInfo, chart_card


def _build_heatmap_finding(
    telemetry: pd.DataFrame,
    flights: pd.DataFrame,
    include_other_routes: bool,
) -> str:
    """Compute a data-driven finding sentence for the flight x time heatmap."""
    active_flights = (
        flights
        if include_other_routes or "in_design" not in flights.columns
        else flights.loc[flights["in_design"]]
    )
    if active_flights.empty or telemetry.empty:
        return "No flights match the active route and sidebar filters."

    climb = summarize_climb_band_by_altitude(telemetry, active_flights)
    n_shown = len(active_flights)
    if climb["max_alt"] > climb["min_alt"] and climb["max_climb_s"] > 0:
        return (
            f"Across the {n_shown} displayed flights, mean Take-off climb duration widens from "
            f"{climb['min_climb_s']:.1f} s at {climb['min_alt']:.0f} m to "
            f"{climb['max_climb_s']:.1f} s at {climb['max_alt']:.0f} m."
        )
    return f"Showing {n_shown} flights aligned from take-off in 2-second telemetry slices."


def render_multivariate_ml(flights: pd.DataFrame, telemetry: pd.DataFrame) -> None:
    """Render the Flight x Time Heatmap card."""
    info = CardInfo(
        title="Flight timelines across the campaign",
        how_to_read=(
            "Each horizontal row is one flight aligned from take-off in 2-second slices, "
            "coloured either by flight phase or electrical power (W). Horizontal black lines "
            "separate the chosen grouping blocks."
        ),
        about=(
            "By default only the 181 R1 design flights are shown; enable 'Include R2-R7' to "
            "compare the other campaign routes alongside them.",
            "Sorting by K-means cluster uses the k value from the Multivariate & ML cluster "
            "slider (default k = 3).",
        ),
        author="Pelin Gül Kızılkılıç",
    )

    with chart_card(info) as card:
        col_order, col_color, col_route = st.columns([2, 2, 1.5])
        order_options = {
            "Altitude": "altitude",
            "Speed": "speed",
            "Payload": "payload",
            "K-means cluster": "cluster",
        }
        color_options = {
            "Phase": "phase",
            "Power (W)": "power",
        }

        with col_order:
            selected_order = st.selectbox(
                "Sort rows by",
                options=list(order_options.keys()),
                index=0,
                key="heatmap_order_by",
            )
        with col_color:
            selected_color = st.selectbox(
                "Colour slices by",
                options=list(color_options.keys()),
                index=0,
                key="heatmap_color_by",
            )
        with col_route:
            include_other_routes = st.checkbox(
                "Include R2-R7",
                value=False,
                key="heatmap_include_other_routes",
            )

        k_val = int(st.session_state.get("kmeans_k", 3))
        fig = build_flight_time_heatmap(
            telemetry=telemetry,
            flights=flights,
            order=order_options[selected_order],
            color=color_options[selected_color],
            include_other_routes=include_other_routes,
            k=k_val,
        )
        card.plot(fig, key="flight_time_heatmap_chart")
        card.finding = _build_heatmap_finding(
            telemetry=telemetry,
            flights=flights,
            include_other_routes=include_other_routes,
        )


def render(tables: dict[str, pd.DataFrame], filters: Any = None) -> None:
    """Entry point called by app.py section router."""
    flights = tables.get("flights", pd.DataFrame())
    telemetry = tables.get("telemetry_1hz", pd.DataFrame())
    render_multivariate_ml(flights, telemetry)
