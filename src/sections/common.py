"""The shared chart card: every chart on the dashboard is shown the same way.

A card has fixed parts, always in this order (docs/interfaces.md, "Card pattern"):

    title        the chart's short name, a few words
    how to read  one or two full sentences: what the marks, axes and colours mean
    controls     the card's own widgets (written by the section)
    chart        the Plotly figure
    finding      optional: one or two sentences computed from what is on screen
    about        a folded box of short paragraphs: why the chart is useful, how it encodes
                 the data, what you can do, the lecture behind it, which flights it uses,
                 and who made it

Sections fill a ``CardInfo`` with the texts and draw their controls and chart inside
``chart_card``:

    @st.fragment
    def sankey_card(tables):
        with chart_card(SANKEY) as card:
            group_by = st.selectbox("Group by", [...], key="sankey_group_by")
            card.plot(build_sankey(...), key="sankey_chart")
            card.finding = describe_sankey(...)  # leave unset when there is nothing to compute
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PLOTLY_CONFIG = {"displaylogo": False}


@dataclass(frozen=True)
class CardInfo:
    """Every fixed text a card shows. Simple English, full sentences (interfaces.md)."""

    title: str  # e.g. "Flight routes"
    how_to_read: str  # e.g. "Each dot is one second of a flight, and its colour shows ..."
    about: tuple[str, ...]  # paragraphs, each made of full sentences
    author: str  # full name, e.g. "İlayda Demir"


class Card:
    """What a section can use inside ``chart_card``."""

    def __init__(self, info: CardInfo) -> None:
        self.info = info
        # One or two sentences about what is on screen now, computed from the filtered data.
        # The box is drawn only when this is set.
        self.finding: str | None = None

    def plot(self, fig: go.Figure, key: str) -> None:
        """Draw a figure the same way on every card."""
        st.plotly_chart(fig, width="stretch", key=key, config=PLOTLY_CONFIG)


@contextmanager
def chart_card(info: CardInfo) -> Iterator[Card]:
    """Draw the fixed parts of a card around the controls and chart a section adds."""
    with st.container(border=True):
        st.subheader(info.title)
        st.caption(info.how_to_read)
        card = Card(info)
        yield card
        if card.finding:
            st.info(card.finding)
        with st.expander("About this chart"):
            st.markdown("\n\n".join([*info.about, f"This chart was made by **{info.author}**."]))


@st.fragment
def render_example_card(
    title: str,
    how_to_read: str,
    tables: dict[str, pd.DataFrame],
    options: dict[str, Callable[[dict[str, pd.DataFrame]], tuple[go.Figure, str]]],
    key_prefix: str,
    about_text: str | None = None,
) -> None:
    """T4 example card (still used by Overview). New charts should use ``chart_card``."""
    with st.container(border=True):
        st.subheader(title)
        st.caption(how_to_read)
        selected_view = st.selectbox(
            "View",
            options=list(options.keys()),
            key=f"{key_prefix}_view",
        )
        fig, finding_text = options[selected_view](tables)
        st.plotly_chart(fig, width="stretch", key=f"{key_prefix}_chart", config=PLOTLY_CONFIG)
        st.info(finding_text)
        # Only cards that say who made them and why get the expander; no default author.
        if about_text:
            with st.expander("About this chart"):
                st.markdown(about_text)
