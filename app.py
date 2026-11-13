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

# The experiment uses payloads 0/250/500 g; any other payload is a single extra flight
# (flight 76 carries 750 g). It stays selectable, but is not selected by default.
design_payloads = set(flights_df.loc[flights_df["in_design"], "payload_g"].astype(int))
n_other_routes = int((flights_df["route"] != "R1").sum())


def payload_label(payload: int) -> str:
    if payload in design_payloads:
        return f"{payload}"
    ids = flights_df.loc[flights_df["payload_g"] == payload, "flight"].astype(int).tolist()
    which = f"flight {ids[0]}" if len(ids) == 1 else "flights " + ", ".join(map(str, ids))
    return f"{payload} ({which}, outside the design)"


with st.sidebar:
    st.header("Global Filters")
    st.caption("Selected filters apply to all dashboard sections.")

    payloads = st.multiselect(
        "Payload (g)",
        options=base_state.payload_options,
        default=[p for p in base_state.payload_options if p in design_payloads],
        format_func=payload_label,
        help="The experiment flew 0, 250 and 500 g. Other payloads are single extra flights.",
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
        f"Include R2–R7 ({n_other_routes} flights on other routes)",
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

# The menu keeps its own value under the "menu_section" key (interfaces.md). Passing a
# `default` that changes on every run would make Streamlit treat it as a new widget and drop
# every second click; `required=True` stops a second click from deselecting the section.
if "menu_section" not in st.session_state:
    st.session_state["menu_section"] = "Overview"

st.segmented_control(
    "Select a dashboard section",
    options=list(sections.keys()),
    key="menu_section",
    required=True,
)
selected_section = st.session_state["menu_section"]

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
