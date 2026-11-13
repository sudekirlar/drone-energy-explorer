"""Energy & Experimental Conditions section: Sankey, treemap, heatmap (owner: Platform).

The cards compare groups of flights by the three settings of the experiment (payload, altitude,
speed). Those comparisons use only the R1 design flights, where the settings are balanced; the
Sankey's "Route" grouping is the one place that uses R2-R7 (see src/charts/sankey.py).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.charts.sankey import build_sankey, describe_sankey
from src.sections.common import CardInfo, chart_card

AUTHOR = "Sude Kırlar"

SANKEY = CardInfo(
    title="Energy budget",
    how_to_read=(
        "Bands flow from groups of flights on the left to the estimated flight phases in the "
        "middle and their parts on the right. A wider band means more energy."
    ),
    about=(
        "A flight's energy is shared between its phases, and the parts add up to the total. A "
        "Sankey diagram shows exactly this kind of budget. It answers two questions: where in "
        "the flight does the energy go, and how does this change with altitude, speed, payload "
        "or route?",
        "The width of a band from a group to a phase is the energy (Wh) that an average flight "
        "of that group spends in that phase. Each phase has the same colour as on the map and "
        "the timeline, and every node is labelled, so the colours are never the only clue. "
        "Hover over a band to see what share of the group's energy it carries.",
        "The phases are estimated from the sensors, because the data has no phase labels. A "
        "flight's phase energies add up exactly to its total energy. The shares of take-off and "
        "landing hardly change when the thresholds of the rule change. The boundary between "
        "cruise and manoeuvre is softer, and those two shares can move by 2 to 4 percentage "
        "points. The drone also uses a very small amount of energy on the ground before "
        "take-off and after landing (under 1% of any flight). The diagram leaves it out.",
        "You can change the groups on the left, hover over a band or a node to read its value "
        "and drag a node to move it.",
        "Altitude, speed and payload compare only the R1 flights of the experiment, because "
        "only there are the three settings balanced. 'Route' uses every flight that passes the "
        "sidebar filters. The other routes have only a few flights each, and they were flown "
        "at different settings from R1, so use this view to describe each route, not to rank "
        "them.",
    ),
    author=AUTHOR,
)

GROUP_OPTIONS = {"Altitude": "altitude", "Speed": "speed", "Payload": "payload", "Route": "route"}


# Sankey node labels take the page's own text colour. Streamlit's chart theme gives Plotly text
# a mid grey that is hard to read on the coloured bands in light mode. Python cannot reliably
# tell which theme the visitor sees (st.context.theme follows the browser, not the theme menu),
# so the colour is left to CSS: "currentColor" is the app's text colour in either theme.
SANKEY_LABEL_CSS = """
<style>
.js-plotly-plot .sankey .node-label { fill: currentColor !important; }
</style>
"""


def render(tables: dict[str, pd.DataFrame]) -> None:
    st.markdown(SANKEY_LABEL_CSS, unsafe_allow_html=True)
    st.markdown("### Energy & Experimental Conditions")
    st.caption(
        "Where the energy goes, and how payload, altitude and speed change it. These charts "
        "compare the R1 flights of the experiment."
    )
    flights = tables.get("flights")
    phase_energy = tables.get("phase_energy")
    if flights is None or phase_energy is None or flights.empty or phase_energy.empty:
        st.info("No flights match the current filters.")
        return

    sankey_card(flights, phase_energy)


@st.fragment
def sankey_card(flights: pd.DataFrame, phase_energy: pd.DataFrame) -> None:
    with chart_card(SANKEY) as card:
        col, _ = st.columns([1, 2])
        label = col.selectbox("Group flights by", list(GROUP_OPTIONS), key="sankey_group_by")
        group_by = GROUP_OPTIONS[label]

        if group_by == "route" and flights["route"].nunique() < 2:
            st.caption("Only R1 is shown. Tick 'Include R2–R7' in the sidebar to compare routes.")

        # Plotly misplaces Sankey nodes when their number changes during an update, so every
        # grouping gets its own chart element and is drawn from scratch.
        card.plot(build_sankey(phase_energy, flights, group_by), key=f"sankey_chart_{group_by}")
        card.finding = describe_sankey(phase_energy, flights, group_by)
