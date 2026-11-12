"""Flight & Temporal section for Drone Delivery Energy Explorer."""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data.filters import FilterState
from src.theme import PALETTES


def render(df: pd.DataFrame, filters: FilterState) -> None:
    """Render Flight & Temporal visualisations."""
    st.markdown("### Flight & Temporal Dynamics")
    st.caption("Note: Flight phases are estimated from telemetry; timestamps are irregular.")

    col1, col2 = st.columns(2)

    with col1:
        if "estimated_phase" in df.columns and "mean_power_w" in df.columns:
            fig_phase = px.violin(
                df,
                x="estimated_phase",
                y="mean_power_w",
                color="estimated_phase",
                box=True,
                color_discrete_map=PALETTES["phase"],
                labels={
                    "estimated_phase": "Estimated Flight Phase",
                    "mean_power_w": "Mean Power (W)",
                },
                title="Power Draw Across Estimated Flight Phases",
            )
            st.plotly_chart(fig_phase, use_container_width=True)

    with col2:
        if "duration_s" in df.columns and "total_energy_wh" in df.columns:
            fig_dur = px.scatter(
                df,
                x="duration_s",
                y="total_energy_wh",
                color="estimated_phase" if "estimated_phase" in df.columns else None,
                color_discrete_map=PALETTES["phase"],
                labels={
                    "duration_s": "Flight Duration (s)",
                    "total_energy_wh": "Total Energy (Wh)",
                    "estimated_phase": "Estimated Phase",
                },
                title="Total Energy vs. Flight Duration",
            )
            st.plotly_chart(fig_dur, use_container_width=True)
