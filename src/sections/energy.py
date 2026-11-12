"""Energy & Experimental Conditions section (owner: Platform, T4 scaffold by UI & ML)."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.theme import PALETTES


def render(tables: dict[str, pd.DataFrame]) -> None:
    """Render Energy & Conditions placeholders aligned with the data contract."""
    flights = tables["flights"]

    st.markdown("### Energy & Experimental Conditions")
    st.caption("Note: mean_airspeed_mps is onboard anemometer airspeed, not ambient wind speed.")

    col1, col2 = st.columns(2)

    with col1:
        plot_df = flights.copy()
        plot_df["speed_label"] = plot_df["speed_mps"].astype(str) + " m/s"
        fig_speed = px.box(
            plot_df,
            x="speed_label",
            y="wh_per_km",
            color="speed_label",
            color_discrete_sequence=PALETTES["viridis"],
            labels={"speed_label": "Target Speed (m/s)", "wh_per_km": "Energy per km (Wh/km)"},
            title="Energy per kilometre (Wh/km) across target speeds",
        )
        fig_speed.update_layout(showlegend=False)
        st.plotly_chart(fig_speed, key="energy_speed_box")

    with col2:
        fig_air = px.scatter(
            flights,
            x="mean_airspeed_mps",
            y="mean_power_w",
            color="altitude_m",
            color_continuous_scale=PALETTES["viridis"],
            labels={
                "mean_airspeed_mps": "Mean Anemometer Airspeed (m/s)",
                "mean_power_w": "Mean Power (W)",
                "altitude_m": "Altitude (m)",
            },
            title="Mean flight power vs. anemometer airspeed",
        )
        st.plotly_chart(fig_air, key="energy_airspeed_scatter")
