"""Shared UI components following the card anatomy in docs/interfaces.md."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


@st.fragment
def render_example_card(
    title: str,
    how_to_read: str,
    tables: dict[str, pd.DataFrame],
    options: dict[str, Callable[[dict[str, pd.DataFrame]], tuple[go.Figure, str]]],
    key_prefix: str,
    about_text: str = "T4 skeleton example card · interaction: select · author: Pelin",
) -> None:
    """Reusable chart card: title -> how to read -> control -> chart -> Finding -> expander."""
    with st.container(border=True):
        st.subheader(title)
        st.caption(f"How to read: {how_to_read}")
        selected_view = st.selectbox(
            "View",
            options=list(options.keys()),
            key=f"{key_prefix}_view",
        )
        fig, finding_text = options[selected_view](tables)
        st.plotly_chart(fig, width="stretch", key=f"{key_prefix}_chart")
        st.info(f"Finding: {finding_text}")
        with st.expander("About this chart"):
            st.markdown(about_text)
