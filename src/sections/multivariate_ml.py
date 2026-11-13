"""Multivariate and ML section (owner: uiml)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.charts.violin import (
    build_phase_payload_violin,
    compute_phase_payload_power,
    summarize_payload_effect,
)
from src.sections.common import CardInfo, chart_card


@st.cache_data(show_spinner=False)
def _cached_phase_power(telemetry: pd.DataFrame, flights: pd.DataFrame) -> pd.DataFrame:
    return compute_phase_payload_power(telemetry, flights)


def _build_violin_finding(phase_power: pd.DataFrame) -> str:
    """Compute a data-driven finding sentence from active phase x payload power values."""
    if phase_power.empty:
        return "No flight phase power observations match the current filter selection."

    stats = summarize_payload_effect(phase_power)
    by_phase = phase_power.groupby("phase")["mean_power_w"].mean().sort_values()
    low_phase, low_w = str(by_phase.index[0]), float(by_phase.iloc[0])
    high_phase, high_w = str(by_phase.index[-1]), float(by_phase.iloc[-1])

    return (
        f"Each +250 g payload step adds {stats['delta_w']:.1f} W (~{stats['delta_pct']:.1f}%) "
        f"on average across all four flight phases ({stats['cruise_delta_w']:.1f} W or "
        f"{stats['cruise_delta_pct']:.1f}% in cruise), while baseline power shifts from "
        f"{low_phase} ({low_w:.0f} W) to {high_phase} ({high_w:.0f} W)."
    )


def render_multivariate_ml(flights: pd.DataFrame, telemetry: pd.DataFrame) -> None:
    """Render the Phase x Payload grouped violin card."""
    design_flights = (
        flights.loc[flights["in_design"]].reset_index(drop=True)
        if "in_design" in flights.columns
        else flights.reset_index(drop=True)
    )

    info = CardInfo(
        title="Power by phase and payload",
        how_to_read=(
            "Each violin shows the distribution of per-flight mean electrical power across the "
            "four active flight phases, shaded from light to dark blue for 0 g, 250 g, and 500 g "
            "payloads. Horizontal bars inside each violin mark the median and interquartile range."
        ),
        about=(
            "Mean power (W) is aggregated per flight within Take-off, Cruise, Manoeuvre, and "
            "Landing on the R1 design flights (181 flights in the default view), excluding Ground.",
            "Use the checkbox to overlay individual flight averages on top of the kernel density.",
        ),
        author="Pelin Gül Kızılkılıç",
    )

    with chart_card(info) as card:
        show_points = st.checkbox(
            "Show flight points",
            value=False,
            key="violin_show_points",
        )

        phase_power = _cached_phase_power(telemetry, design_flights)
        fig = build_phase_payload_violin(
            phase_power,
            show_points=show_points,
            cut_y_axis=True,
        )
        card.plot(fig, key="violin_chart")
        card.finding = _build_violin_finding(phase_power)


def render(tables: dict[str, pd.DataFrame], filters: Any = None) -> None:
    """Entry point called by app.py section router."""
    flights = tables.get("flights", pd.DataFrame())
    telemetry = tables.get("telemetry_1hz", pd.DataFrame())
    render_multivariate_ml(flights, telemetry)
