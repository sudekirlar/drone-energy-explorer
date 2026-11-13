"""Overview & Data Quality section (owner: Data, T4 scaffold by UI & ML)."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.data.schema import data_dictionary
from src.sections.common import render_example_card
from src.theme import PALETTES


def _build_energy_by_payload(tables: dict[str, pd.DataFrame]) -> tuple[go.Figure, str]:
    flights = tables["flights"]
    plot_df = flights.copy()
    plot_df["payload_label"] = plot_df["payload_g"].astype(str) + " g"
    order = [f"{p} g" for p in sorted(flights["payload_g"].dropna().unique())]
    color_map = {f"{k} g": v for k, v in PALETTES["payload"].items()}

    fig = px.box(
        plot_df,
        x="payload_label",
        y="energy_wh",
        color="payload_label",
        category_orders={"payload_label": order},
        color_discrete_map=color_map,
        labels={"payload_label": "Payload (g)", "energy_wh": "Total Energy (Wh)"},
        title="Total flight energy (Wh) across payload groups",
    )
    fig.update_layout(showlegend=False)

    medians = flights.groupby("payload_g")["energy_wh"].median().sort_index()
    if len(medians) >= 2:
        low_p, high_p = medians.index[0], medians.index[-1]
        finding = (
            f"Filtered median energy shifts from {medians.iloc[0]:.1f} Wh at {low_p} g "
            f"to {medians.iloc[-1]:.1f} Wh at {high_p} g."
        )
    elif len(medians) == 1:
        only_p = medians.index[0]
        finding = f"Filtered median energy for {only_p} g payload is {medians.iloc[0]:.1f} Wh."
    else:
        finding = "No flights available in the current filter selection."

    return fig, finding


def _build_wh_per_km_by_speed(tables: dict[str, pd.DataFrame]) -> tuple[go.Figure, str]:
    flights = tables["flights"]
    plot_df = flights.copy()
    plot_df["speed_label"] = plot_df["speed_mps"].astype(str) + " m/s"
    order = [f"{s} m/s" for s in sorted(flights["speed_mps"].dropna().unique())]

    fig = px.box(
        plot_df,
        x="speed_label",
        y="wh_per_km",
        color="speed_label",
        category_orders={"speed_label": order},
        color_discrete_sequence=PALETTES["viridis"],
        labels={"speed_label": "Target Speed (m/s)", "wh_per_km": "Energy per km (Wh/km)"},
        title="Energy per kilometre (Wh/km) across target speeds",
    )
    fig.update_layout(showlegend=False)

    medians = flights.groupby("speed_mps")["wh_per_km"].median().sort_values()
    if not medians.empty:
        best_s = medians.index[0]
        finding = (
            f"Lowest median energy intensity in the current selection is {medians.iloc[0]:.1f} "
            f"Wh/km at {best_s} m/s."
        )
    else:
        finding = "No flights available in the current filter selection."

    return fig, finding


def render(tables: dict[str, pd.DataFrame]) -> None:
    """Render Pelin's shared T4 card with Data's E1 KPIs and quality evidence."""
    flights = tables["flights"]
    st.markdown("### Overview & Data Quality")

    if flights.empty:
        st.info("No flights match the current filter selection.")
        return

    cols = st.columns(4)
    cols[0].metric("Flights", f"{flights['flight'].nunique():,}")
    cols[1].metric("Total flight duration", f"{flights['duration_s'].sum() / 3600:,.1f} h")
    cols[2].metric("Total GPS distance", f"{flights['distance_m'].sum() / 1000:,.1f} km")
    cols[3].metric("Median energy", f"{flights['energy_wh'].median():,.1f} Wh")

    render_example_card(
        title="Energy consumption across experimental conditions",
        how_to_read=(
            "Each box shows the median, interquartile range, and spread across filtered flights."
        ),
        tables=tables,
        options={
            "Total Energy (Wh) by Payload": _build_energy_by_payload,
            "Energy per km (Wh/km) by Speed": _build_wh_per_km_by_speed,
        },
        key_prefix="overview_example",
        about_text=(
            "CMU drone flight telemetry. These box plots compare the currently filtered "
            "flights; they do not establish causation or generalize to other drones. "
            "Data preparation and limitations are documented below."
        ),
    )

    st.markdown("#### Dataset context")
    st.caption(
        "CMU drone flight telemetry (DJI Matrice 100), routes R1–R7. "
        "Ground and stationary hover tests are excluded from flight comparisons. "
        "Battery power is voltage × current; energy is integrated at the original "
        "sampling rate before 1 Hz resampling. Results should not be generalized "
        "to other aircraft, batteries, locations or weather conditions."
    )

    st.markdown("#### Data cleaning and provenance")
    quality = tables.get("quality_log")
    if quality is None or quality.empty:
        st.warning("Quality log is not available for the current data source.")
    else:
        quality_columns = [
            "rule_id",
            "description",
            "rows_affected",
            "flights_affected",
            "iso25012",
        ]
        st.dataframe(quality[quality_columns], width="stretch", hide_index=True)
        if (quality["rule_id"] == "joint-deviation-outliers").any():
            st.caption(
                "Outlier counts depend on the documented detection rule. Flagged "
                "flights are retained; the implementation and original D4 prototype "
                "reported different counts, which should not be conflated."
            )

    st.markdown("#### ISO/IEC 25012 quality considerations")
    quality_notes = pd.DataFrame(
        [
            ("Accuracy", "Negative current clipping and inferred clock fixes are documented."),
            ("Completeness", "Missing telemetry and time gaps require inspection."),
            ("Consistency", "Route inclusion and outlier flags use explicit rules."),
            ("Credibility", "Estimated flight phases are not independent ground truth."),
            ("Traceability", "Original local times are kept alongside corrected times."),
        ],
        columns=["Characteristic", "Evidence / limitation"],
    )
    st.dataframe(quality_notes, width="stretch", hide_index=True)
    st.caption(
        "No statistically significant day effect was detected in the energy residuals "
        "(Kruskal–Wallis, p ≈ 0.09; see D1 in docs/decisions.md)."
    )

    with st.expander("Data dictionary · columns, units and producers"):
        st.dataframe(
            pd.DataFrame(data_dictionary()),
            width="stretch",
            hide_index=True,
        )
