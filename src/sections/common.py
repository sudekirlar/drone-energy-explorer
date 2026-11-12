"""Shared UI components and the reusable example card."""

from collections.abc import Callable

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


@st.fragment
def render_example_card(
    title: str,
    df: pd.DataFrame,
    options: dict[str, Callable[[pd.DataFrame], tuple[go.Figure, str]]],
    key_prefix: str,
) -> None:
    """Reusable interactive chart card with fragment isolation and finding box."""
    with st.container(border=True):
        st.markdown(f"#### {title}")
        selected_metric = st.selectbox(
            "Select metric / view",
            options=list(options.keys()),
            key=f"{key_prefix}_selectbox",
        )
        fig, finding_text = options[selected_metric](df)
        st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_chart")
        st.info(f"**Finding:** {finding_text}")
