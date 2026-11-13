"""Overview & Data Quality (E1). Owner: Data."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data.schema import data_dictionary
from src.theme import PALETTES


def render(tables: dict[str, pd.DataFrame]) -> None:
    st.markdown("### Overview & Data Quality")
    flights = tables["flights"]
    if flights.empty:
        st.info("No flights match the current filter selection.")
        return

    cols = st.columns(4)
    cols[0].metric("Flights", f"{flights['flight'].nunique():,}")
    cols[1].metric("Total flight duration", f"{flights['duration_s'].sum() / 3600:,.1f} h")
    cols[2].metric("Total GPS distance", f"{flights['distance_m'].sum() / 1000:,.1f} km")
    cols[3].metric("Median energy", f"{flights['energy_wh'].median():,.1f} Wh")

    st.markdown("#### Dataset context")
    st.markdown(
        "CMU drone flight telemetry, recorded with a DJI Matrice 100 in a controlled "
        "experimental setting. The analyzed data covers routes R1–R7; ground and "
        "stationary hover tests are excluded from flight comparisons. Power is "
        "calculated from battery voltage and current; energy is integrated at the "
        "original sampling rate before resampling to 1 Hz. Results should not be "
        "generalized to different aircraft, batteries, terrain or weather conditions."
    )

    with st.container(border=True):
        st.markdown("#### Energy consumption across experiment settings")
        metric = st.selectbox(
            "Comparison",
            ["Total energy by payload", "Energy per kilometre by target speed"],
            key="overview_metric_select",
        )
        plot = flights.copy()
        if metric == "Total energy by payload":
            plot["payload"] = plot["payload_g"].astype(str) + " g"
            fig = px.box(
                plot,
                x="payload",
                y="energy_wh",
                color="payload",
                labels={"payload": "Payload", "energy_wh": "Energy (Wh)"},
                title="How does total energy vary with payload?",
                color_discrete_sequence=list(PALETTES["payload"].values()),
            )
            center = flights.groupby("payload_g")["energy_wh"].median()
            caption = "Median energy by payload in the current selection: " + ", ".join(
                f"{k} g = {v:.1f} Wh" for k, v in center.items()
            )
        else:
            plot["speed"] = plot["speed_mps"].astype(str) + " m/s"
            fig = px.box(
                plot,
                x="speed",
                y="wh_per_km",
                color="speed",
                labels={"speed": "Target speed", "wh_per_km": "Energy intensity (Wh/km)"},
                title="How does energy intensity vary with target speed?",
                color_discrete_sequence=PALETTES["viridis"],
            )
            center = flights.groupby("speed_mps")["wh_per_km"].median()
            caption = "Median energy intensity by speed in the current selection: " + ", ".join(
                f"{k} m/s = {v:.1f} Wh/km" for k, v in center.items()
            )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True, key="overview_comparison_chart")
        st.info(f"**Finding:** {caption}")

    st.markdown("#### Data cleaning and provenance")
    quality = tables.get("quality_log")
    if quality is None or quality.empty:
        st.warning("No quality log loaded. Cleaning-rule counts are not available.")
    else:
        st.dataframe(
            quality[["rule_id", "description", "rows_affected", "flights_affected", "iso25012"]],
            use_container_width=True,
            hide_index=True,
        )
        if (quality["rule_id"] == "joint-deviation-outliers").any():
            st.caption(
                "Outlier count depends on the documented detection rule; flagged "
                "flights are retained. The current implementation and the original "
                "D4 prototype report differ, so do not treat the counts as interchangeable."
            )

    st.markdown("#### ISO/IEC 25012 quality considerations")
    iso = pd.DataFrame(
        [
            ("Accuracy", "Negative current clipping; inferred clock corrections documented."),
            ("Completeness", "Missing telemetry and time gaps require inspection."),
            ("Consistency", "Route filtering and outlier flags follow named rules."),
            (
                "Credibility",
                "Estimated flight phases are not independently annotated ground truth.",
            ),
            ("Traceability", "Original local time is retained alongside inferred correction."),
        ],
        columns=["Characteristic", "Evidence / limitation"],
    )
    st.dataframe(iso, hide_index=True, use_container_width=True)
    st.caption("No day-to-day significance claim is made without a documented statistical test.")

    with st.expander("Data dictionary · columns, units and producers"):
        st.dataframe(pd.DataFrame(data_dictionary()), hide_index=True, use_container_width=True)
