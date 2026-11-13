"""The shared chart card: every chart on the dashboard is shown the same way.

A card has fixed parts, always in this order (docs/interfaces.md, "Card pattern"):

    title        the chart's main message, as one plain sentence
    how to read  one sentence: what the marks, axes and colours mean
    data         one sentence: which flights the chart uses, and why
    controls     the card's own widgets (written by the section)
    chart        the Plotly figure
    finding      what the real data shows, with numbers
    about        a folded box: why this chart, what you see, what you can do,
                 the lecture it comes from, and who made it

Sections fill a ``CardInfo`` with the texts and draw their controls and chart inside
``chart_card``:

    @st.fragment
    def sankey_card(tables):
        with chart_card(SANKEY) as card:
            group_by = st.selectbox("Group by", [...], key="sankey_group_by")
            card.plot(build_sankey(...), key="sankey_chart")
            card.finding = f"At 100 m, take-off and landing use {share:.0%} of the energy."
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
    """Every text a card shows. Write simple English in full sentences (interfaces.md)."""

    title: str  # the main message, e.g. "Fast flights spend more energy in waypoint turns."
    how_to_read: str  # e.g. "Each line is one flight; its colour shows the power at that moment."
    data: str  # e.g. "The 181 R1 design flights, because only they form a balanced experiment."
    finding: str  # the default finding; a card may replace it with a computed one
    why: str  # why this chart type suits this data and this question
    encoding: str  # which visual channel shows which variable, and why
    interaction: str  # what the user can do, named with Yi et al.'s types
    lecture: str  # the lecture and the idea it applies
    author: str  # full name of the person who made the chart


class Card:
    """What a section can use inside ``chart_card``."""

    def __init__(self, info: CardInfo) -> None:
        self.info = info
        self.finding: str | None = None  # set this to replace info.finding with live numbers

    def plot(self, fig: go.Figure, key: str) -> None:
        """Draw a figure the same way on every card."""
        st.plotly_chart(fig, width="stretch", key=key, config=PLOTLY_CONFIG)


@contextmanager
def chart_card(info: CardInfo) -> Iterator[Card]:
    """Draw the fixed parts of a card around the controls and chart a section adds."""
    with st.container(border=True):
        st.subheader(info.title)
        st.caption(f"**How to read:** {info.how_to_read}  \n**Data:** {info.data}")
        card = Card(info)
        yield card
        st.info(f"**Finding:** {card.finding or info.finding}")
        with st.expander("About this chart"):
            st.markdown(
                f"**Why this chart.** {info.why}\n\n"
                f"**What you see.** {info.encoding}\n\n"
                f"**What you can do.** {info.interaction}\n\n"
                f"**From the lectures.** {info.lecture}\n\n"
                f"**Made by** {info.author}."
            )


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
        st.caption(f"**How to read:** {how_to_read}")
        selected_view = st.selectbox(
            "View",
            options=list(options.keys()),
            key=f"{key_prefix}_view",
        )
        fig, finding_text = options[selected_view](tables)
        st.plotly_chart(fig, width="stretch", key=f"{key_prefix}_chart", config=PLOTLY_CONFIG)
        st.info(f"**Finding:** {finding_text}")
        # Only cards that say who made them and why get the expander; no default author.
        if about_text:
            with st.expander("About this chart"):
                st.markdown(about_text)
