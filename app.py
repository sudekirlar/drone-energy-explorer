"""Main application for Drone Delivery Energy Explorer."""

import streamlit as st

from src.data.filters import FilterState, apply_filters
from src.data.loader import load_flights
from src.sections import (
    energy,
    flight_temporal,
    multivariate_ml,
    overview,
)
from src.theme import apply_theme


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="Drone Delivery Energy Explorer",
    page_icon="🚁",
    layout="wide",
)

apply_theme()

st.title("🚁 Drone Delivery Energy Explorer")
st.markdown(
    """
    Explore how payload, target speed, and altitude
    influence drone energy consumption.
    """
)


# ==================================================
# DATA LOADING
# ==================================================

@st.cache_data(show_spinner="Loading flight data...")
def get_flight_data():
    """Load validated flight-level data."""
    return load_flights()


try:
    data = get_flight_data()
except Exception as error:
    st.error("An error occurred while loading flight data.")
    st.exception(error)
    st.stop()

if data.empty:
    st.warning("The flight dataset is empty.")
    st.stop()

if "is_synthetic" in data.columns and data["is_synthetic"].any():
    st.warning(
        "⚠️ **Demo Mode:** No CSV dataset was found in `data/`. "
        "Displaying synthetic placeholder data. Add `data/flight_summary.csv` to use real flight records."
    )


# ==================================================
# GLOBAL FILTERS
# ==================================================

base_filters = FilterState.from_dataframe(data)

with st.sidebar:
    st.header("Global Filters")
    st.caption("The selected filters apply to all dashboard sections.")

    payloads = st.multiselect(
        "Payload (g)",
        options=base_filters.payload_options,
        default=base_filters.payload_options,
    )

    altitudes = st.multiselect(
        "Altitude (m)",
        options=base_filters.altitude_options,
        default=base_filters.altitude_options,
    )

    speeds = st.multiselect(
        "Target Speed (m/s)",
        options=base_filters.speed_options,
        default=base_filters.speed_options,
    )

    hide_flagged = st.checkbox(
        "Hide outlier flights",
        value=False,
    )

    include_other_routes = st.checkbox(
        "Include other routes (R2–R7)",
        value=True,
    )


# ==================================================
# FILTER STATE & APPLICATION
# ==================================================

filters = FilterState(
    payloads=tuple(payloads),
    altitudes=tuple(altitudes),
    speeds=tuple(speeds),
    hide_flagged=hide_flagged,
    include_other_routes=include_other_routes,
)

filtered_data = apply_filters(data, filters)

if filtered_data.empty:
    st.warning("No flights match the selected filters.")
    st.info("Try changing your filter selections.")
    st.stop()


# ==================================================
# DASHBOARD NAVIGATION
# ==================================================

st.subheader("Dashboard")

sections = {
    "Overview": overview,
    "Flight & Temporal": flight_temporal,
    "Energy & Conditions": energy,
    "Multivariate & ML": multivariate_ml,
}

selected_section = st.segmented_control(
    "Select a dashboard section",
    options=list(sections.keys()),
    default="Overview",
    selection_mode="single",
)

if selected_section is None:
    selected_section = "Overview"

st.divider()

sections[selected_section].render(filtered_data, filters)


# ==================================================
# SIDEBAR STATISTICS
# ==================================================

with st.sidebar:
    st.divider()
    st.subheader("Dataset Statistics")

    number_of_flights = (
        filtered_data["flight"].nunique()
        if "flight" in filtered_data.columns
        else len(filtered_data)
    )

    st.metric(label="Filtered Flights", value=f"{number_of_flights:,}")
    st.metric(label="Records", value=f"{len(filtered_data):,}")
    st.caption("Drone Delivery Energy Explorer")
