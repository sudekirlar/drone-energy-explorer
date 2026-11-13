"""Main application for Drone Delivery Energy Explorer."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data import loader, schema
from src.data.filters import FilterState, apply_filters
from src.sections import (
    energy,
    flight_temporal,
    multivariate_ml,
    overview,
)
from src.theme import register_plotly_template

# ==================================================
# PAGE CONFIGURATION & THEME
# ==================================================

st.set_page_config(
    page_title="Drone Delivery Energy Explorer",
    page_icon="🚁",
    layout="wide",
)

register_plotly_template()

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==================================================
# DATA LOADING (UI LAYER CACHING)
# ==================================================


@st.cache_data(show_spinner="Loading contract tables...")
def get_table(name: str) -> pd.DataFrame:
    return loader.load_table(name)


@st.cache_data(show_spinner=False)
def get_ml_metrics() -> dict:
    return loader.load_ml_metrics()


tables: dict[str, pd.DataFrame] = {}
sample_tables: list[str] = []

try:
    for table_name in schema.TABLES:
        source = loader.table_source(table_name)
        if source is not None:
            tables[table_name] = get_table(table_name)
            if source == "sample":
                sample_tables.append(table_name)
except loader.SchemaError as error:
    st.error("Loaded data does not match the data contract.")
    st.caption(str(error))
    st.stop()

header_col, badge_col = st.columns([5, 1])
with header_col:
    st.title("🚁 Drone Delivery Energy Explorer")
    st.markdown(
        "Explore how payload, target speed, and altitude influence drone energy consumption."
    )
with badge_col:
    if sample_tables:
        st.caption("🟡 **sample data**")

if "flights" not in tables or tables["flights"].empty:
    st.info("Sample tables are coming with T5. Add contract tables under `data/` to explore.")
    st.stop()


# ==================================================
# GLOBAL FILTERS
# ==================================================

flights_df = tables["flights"]
base_state = FilterState.from_flights(flights_df)

with st.sidebar:
    st.header("Global Filters")
    st.caption("Selected filters apply to all dashboard sections.")

    payloads = st.multiselect(
        "Payload (g)",
        options=base_state.payload_options,
        default=base_state.payload_options,
    )

    altitudes = st.multiselect(
        "Altitude (m)",
        options=base_state.altitude_options,
        default=base_state.altitude_options,
    )

    speeds = st.multiselect(
        "Target Speed (m/s)",
        options=base_state.speed_options,
        default=base_state.speed_options,
    )

    hide_outliers = st.checkbox(
        "Hide outlier flights",
        value=False,
    )

    include_other_routes = st.checkbox(
        "Include R2–R7",
        value=False,
    )

filter_state = FilterState(
    payloads=tuple(payloads),
    altitudes=tuple(altitudes),
    speeds=tuple(speeds),
    include_missing_altitude=True,
    hide_outliers=hide_outliers,
    include_other_routes=include_other_routes,
)

filtered_tables = apply_filters(tables, filter_state)
filtered_flights = filtered_tables["flights"]

if filtered_flights.empty:
    st.warning("No flights match the selected filters.")
    st.info("Try changing your filter selections.")
    st.stop()


# ==================================================
# DASHBOARD NAVIGATION
# ==================================================

sections = {
    "Overview": overview,
    "Flight & Temporal": flight_temporal,
    "Energy & Conditions": energy,
    "Multivariate & ML": multivariate_ml,
}

if "menu_section" not in st.session_state:
    st.session_state["menu_section"] = "Overview"

selected_section = st.segmented_control(
    "Select a dashboard section",
    options=list(sections.keys()),
    default=st.session_state["menu_section"],
    selection_mode="single",
)

if selected_section is None:
    selected_section = "Overview"

st.session_state["menu_section"] = selected_section

st.divider()

sections[selected_section].render(filtered_tables)


# ==================================================
# SIDEBAR STATISTICS
# ==================================================

with st.sidebar:
    st.divider()
    st.subheader("Dataset Statistics")
    st.metric(label="Filtered Flights", value=f"{filtered_flights['flight'].nunique():,}")
    st.metric(label="Records", value=f"{len(filtered_flights):,}")
