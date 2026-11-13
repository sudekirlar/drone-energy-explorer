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


def _build_pcp_finding(summary: pd.DataFrame, silhouette: float) -> str:
    """Build a data-driven finding sentence from cluster_summary and silhouette score."""
    ordered = summary.sort_values("mean_energy_wh", ascending=True).reset_index(drop=True)
    low = ordered.iloc[0]
    high = ordered.iloc[-1]
    k = len(ordered)

    base = (
        f"Group 1 ({int(low['n_flights'])} flights) uses {low['mean_energy_wh']:.1f} Wh on average "
        f"and Group {k} ({int(high['n_flights'])} flights) uses {high['mean_energy_wh']:.1f} Wh."
    )

    detail = ""
    if k >= 3:
        prev = ordered.iloc[-2]
        power_diff = abs(high["mean_cruise_power_w"] - prev["mean_cruise_power_w"])
        if power_diff <= 15.0:
            detail = (
                f" Groups {k - 1} and {k} have almost the same cruise power "
                f"({prev['mean_cruise_power_w']:.0f} W and {high['mean_cruise_power_w']:.0f} W); "
                f"Group {k} uses more energy because its flights last longer "
                f"({high['mean_duration_s']:.0f} s against {prev['mean_duration_s']:.0f} s)."
            )
        else:
            detail = (
                f" Group {k} draws {high['mean_cruise_power_w']:.0f} W in cruise against "
                f"{prev['mean_cruise_power_w']:.0f} W in Group {k - 1}."
            )

    overlap_note = (
        f" The silhouette score of {silhouette:.2f} means that the groups overlap "
        "rather than forming hard categories."
    )
    return base + detail + overlap_note


def render_multivariate_ml(flights: pd.DataFrame) -> None:
    """Render the Parallel Coordinates Plot and cached K-means card."""
    design_flights = (
        flights.loc[flights["in_design"]].reset_index(drop=True)
        if "in_design" in flights.columns
        else flights.reset_index(drop=True)
    )

    info = CardInfo(
        title="Flight groups",
        how_to_read=(
            "Each polyline is one experimental flight across nine telemetry measures and its "
            "K-means group. Drag any axis label left or right to reorder dimensions, or drag "
            "vertically along an axis to brush a subset of flights."
        ),
        about=(
            "This view groups the R1 design flights (181 flights in the default view) using "
            "K-means clustering on standardized energy, Wh/km, duration, cruise power, and "
            "climb power; payload is not used as a clustering feature, and the anemometer "
            "channel is excluded.",
            "Groups are ordered from lowest to highest mean energy consumption so that Group 1 "
            "always denotes the lowest-energy flights for the chosen k.",
        ),
        author="Pelin Gül Kızılkılıç",
    )

    with chart_card(info) as card:
        col_slider, col_metric = st.columns([3, 1])
        with col_slider:
            k = st.slider(
                "Number of K-means clusters (k)",
                min_value=2,
                max_value=6,
                value=3,
                step=1,
                key="kmeans_k",
            )

        if len(design_flights) < k:
            st.warning("Not enough filtered flights to form the requested number of clusters.")
            return

        result = _cached_kmeans(design_flights, k=k)
        with col_metric:
            st.metric("Silhouette score", f"{result.silhouette:.3f}")

        fig = build_pcp(design_flights, result.labels)
        card.plot(fig, key="pcp_chart")
        card.finding = _build_pcp_finding(result.cluster_summary, result.silhouette)


def render(tables: dict[str, pd.DataFrame], filters: Any = None) -> None:
    """Entry point called by app.py section router."""
    flights = tables.get("flights", pd.DataFrame())
    render_multivariate_ml(flights)
