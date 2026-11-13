"""Multivariate and ML section (owner: uiml)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.charts.pcp import build_pcp
from src.ml.clustering import run_kmeans
from src.sections.common import CardInfo, chart_card


@st.cache_data(show_spinner=False)
def _cached_kmeans(flights: pd.DataFrame, k: int):
    return run_kmeans(flights, k=k)


def render_multivariate_ml(flights: pd.DataFrame) -> None:
    """Render the Parallel Coordinates Plot and cached K-means card."""
    design_flights = (
        flights.loc[flights["in_design"]].reset_index(drop=True)
        if "in_design" in flights.columns
        else flights.reset_index(drop=True)
    )

    info = CardInfo(
        title="Flight behavioral regimes across nine telemetry measures",
        question="Which flights behave alike across payload, speed, power, and energy measures?",
        takeaway=(
            "K-means groups flights along an energy-intensity gradient, yet clusters overlap "
            "and represent continuous regimes rather than hard categories; flight duration "
            "also indirectly encodes cruise speed over fixed-length legs."
        ),
        how_to_read=(
            "Drag any axis label left or right to reorder dimensions, or drag vertically "
            "along an axis to brush a subset of flights. Cluster colours remain fixed to "
            "G1–G6 ordered from lowest to highest mean energy."
        ),
        data_note=(
            "Experimental design flights (R1–R6, in_design = True), "
            "excluding the anemometer channel."
        ),
    )

    with chart_card(info):
        col_slider, col_metric = st.columns([3, 1])
        with col_slider:
            k = st.slider(
                "Number of K-means clusters (k)",
                min_value=2,
                max_value=6,
                value=3,
                step=1,
                key="pcp_kmeans_k",
            )

        if len(design_flights) < k:
            st.warning("Not enough filtered flights to form the requested number of clusters.")
            return

        result = _cached_kmeans(design_flights, k=k)
        with col_metric:
            st.metric("Silhouette score", f"{result.silhouette:.3f}")

        fig = build_pcp(design_flights, result.labels, max_k=6)
        st.plotly_chart(fig, use_container_width=True)


def render(tables: dict[str, pd.DataFrame], filters: Any = None) -> None:
    """Entry point called by app.py section router."""
    flights = tables.get("flights", pd.DataFrame())
    render_multivariate_ml(flights)
