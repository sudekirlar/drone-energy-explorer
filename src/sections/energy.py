"""Energy & Conditions section for Drone Delivery Energy Explorer."""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data.filters import FilterState
from src.theme import PALETTES


def render(df: pd.DataFrame, filters: FilterState) -> None:
    """Render Energy & Environmental Conditions visualisations."""
    st.markdown("### Energy & Operating Conditions")
    st.caption("Note: `wind_speed` represents onboard anemometer airspeed, not ambient wind.")

    col1, col2 = st.columns(2)

    with col1:
        speed_col = "target_speed" if "target_speed" in df.columns else "speed"
        if speed_col in df.columns and "energy_per_km_wh" in df.columns:
            fig_speed = px.box(
                df,
                x=speed_col,
                y="energy_per_km_wh",
                color=speed_col,
                color_discrete_sequence=PALETTES["viridis"],
                labels={
                    speed_col: "Target Speed (m/s)",
                    "energy_per_km_wh": "Energy per km (Wh/km)",
                },
                title="Energy Efficiency (Wh/km) vs. Target Speed",
            )
            st.plotly_chart(fig_speed, use_container_width=True)

    with col2:
        if "wind_speed" in df.columns and "mean_power_w" in df.columns:
            fig_wind = px.scatter(
                df,
                x="wind_speed",
                y="mean_power_w",
                color="target_altitude" if "target_altitude" in df.columns else None,
                color_continuous_scale=PALETTES["viridis"],
                labels={
                    "wind_speed": "Anemometer Airspeed (m/s)",
                    "mean_power_w": "Mean Power (W)",
                    "target_altitude": "Altitude (m)",
                },
                title="Mean Power vs. Anemometer Airspeed",
            )
            st.plotly_chart(fig_wind, use_container_width=True)
