"""Entry point of the dashboard.

T0 placeholder: proves that the repo deploys to Streamlit Community Cloud.
T4 replaces this with the real frame (menu, sidebar filters, sections).
"""

import sys

import streamlit as st

st.set_page_config(
    page_title="Drone Delivery Energy Explorer",
    page_icon=":material/flight:",
    layout="wide",
)

st.title("Drone Delivery Energy Explorer")
st.write(
    "How do payload, cruise speed, altitude and wind shape the energy a delivery drone "
    "spends, and where in the flight does that energy go?"
)
st.info("Work in progress: the dashboard skeleton is being built.", icon=":material/construction:")

# Shown on purpose: lets us check on the live link which Python the cloud really uses.
st.caption(f"Python {sys.version.split()[0]} · Streamlit {st.__version__}")
