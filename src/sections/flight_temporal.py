"""Flight & Temporal Analysis section (owner: Data, T4 scaffold by UI & ML)."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.theme import PALETTES


def render(tables: dict[str, pd.DataFrame]) -> None:
    """Render Flight & Temporal placeholders aligned with the data contract."""
    flights = tables["flights"]
    phase_energy = tables.get("phase_energy", pd.DataFrame())

    st.markdown("### Flight & Temporal Analysis")
    st.caption(
        "Flight phases are estimated by the phase rule; raw telemetry timestamps are irregular."
    )

    col1, col2 = st.columns(2)

    with col1:
        if not phase_energy.empty:
            fig_phase = px.box(
                phase_energy,
                x="phase",
                y="energy_wh",
                color="phase",
                color_discrete_map=PALETTES["phase"],
                labels={"phase": "Estimated Phase", "energy_wh": "Phase Energy (Wh)"},
                title="Estimated phase energy distribution across flights",
            )
            fig_phase.update_layout(showlegend=False)
            st.plotly_chart(fig_phase, key="temporal_phase_box")

    with col2:
        fig_dur = px.scatter(
            flights,
            x="duration_s",
            y="energy_wh",
            color="route",
            color_discrete_sequence=PALETTES["categorical"],
            labels={
                "duration_s": "Flight Duration (s)",
                "energy_wh": "Total Energy (Wh)",
                "route": "Route",
            },
            title="Total energy scales linearly with flight duration",
        )
        st.plotly_chart(fig_dur, key="temporal_duration_scatter")
