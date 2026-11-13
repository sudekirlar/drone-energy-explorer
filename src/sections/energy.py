"""Energy & Experimental Conditions section (owner: Platform)."""

from __future__ import annotations

import pandas as pd
import streamlit as st


def render(tables: dict[str, pd.DataFrame]) -> None:
    """Render placeholder until Platform section charts land."""
    st.markdown("### Energy & Experimental Conditions")
    st.info("Charts coming in #9 (Energy & Experimental Conditions).")
