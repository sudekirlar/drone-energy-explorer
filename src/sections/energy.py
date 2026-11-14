"""Energy & Experimental Conditions section: Sankey, treemap, heatmap (owner: Platform).

The cards compare groups of flights by the three settings of the experiment (payload, altitude,
speed). Those comparisons use only the R1 design flights, where the settings are balanced; the
Sankey's "Route" grouping is the one place that uses R2-R7 (see src/charts/sankey.py).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.charts.payload_heatmap import (
    build_importance,
    build_payload_heatmap,
    build_prediction_scatter,
    describe_payload_heatmap,
    model_scores,
)
from src.charts.sankey import build_sankey, describe_sankey
from src.charts.treemap import build_treemap, describe_treemap
from src.data import loader
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

TREE = CardInfo(
    title="Cost of each setting",
    how_to_read=(
        "Each box is a group of R1 flights, split by payload, altitude and speed. A darker box "
        "uses less energy per kilometre, and a yellow box uses more. Click a box to zoom in, and "
        "click the top bar (or the centre of the sunburst) to zoom out."
    ),
    about=(
        "The R1 experiment flew every combination of 3 payloads, 4 altitudes and 5 speeds, which "
        "makes 60 settings. Arranged as a tree, these settings become the leaves of three levels. "
        "The chart answers two questions: which setting is the cheapest per kilometre, and how "
        "does the order change as you go down the tree?",
        "The size of a box shows how many flights it holds. The experiment flew almost every "
        "setting three times, so the boxes are almost equal. This is honest, but it also means "
        "that the colour carries the result. The colour is the median energy per kilometre "
        "(Wh/km) of the flights in the box, on one sequential scale (Viridis). The median is "
        "used because a single unusual flight cannot move it much.",
        "This is not a natural hierarchy. Payload is not the parent of altitude; we chose the "
        "order of the levels. That is why you can change it, and each order puts a different "
        "setting at the top.",
        "You can switch between three drawings of the same tree. A treemap uses the whole area "
        "and leaves room for colour, but boxes of different shapes are hard to compare by size. "
        "An icicle shows the depth of the tree clearly. A sunburst gives the outer levels more "
        "room, but angles are harder to read than lengths. The icicle and the sunburst open "
        "with two levels, because 60 settings would be too thin to read; click a box to see "
        "the level below it. Hover over a box to read its median "
        "and its number of flights.",
        "The chart uses only the R1 flights of the experiment, because only there are the three "
        "settings balanced. One setting (0 g, 25 m and 4 m/s) has a single R1 flight, and two "
        "settings have two, so their colours rest on fewer flights.",
    ),
    author=AUTHOR,
)

HEATMAP = CardInfo(
    title="Payload, speed and cruise power",
    how_to_read=(
        "Each cell holds the R1 flights with one payload and one target speed. Its colour and "
        "number show their mean cruise power (W), or, in the two difference views, how far a "
        "model's prediction is from the measurement."
    ),
    about=(
        "This chart answers the main question of the dashboard most directly: how do payload "
        "and speed change the power a drone needs? It uses cruise power, the mean power on the "
        "straight legs, because it does not depend on how long the take-off and the landing "
        "take. Altitude barely changes cruise power; its cost is in climbing and descending, "
        "which the energy budget above shows. Use the sidebar to look at one altitude.",
        "The same grid also shows a machine-learning model. A Random Forest is a set of many "
        "decision trees. Each tree asks yes-or-no questions such as 'is the payload above "
        "375 g?' and ends with a power value, and the forest averages the answers of all its "
        "trees. It predicts a flight's cruise power from its payload, speed and altitude. Every "
        "prediction on this chart comes from a model that never saw that flight (5-fold "
        "cross-validation, repeated with 5 different splits).",
        "We compare the forest with a straight-line (linear) model. The forest is only worth "
        "using where the straight line fails. The two difference views share one colour scale, "
        "so you can compare them directly: blue means the model predicted too much, red means "
        "it predicted too little, and grey means it was right. The gain over the linear model "
        "is small, and the scores above show by how much.",
        "The bar chart shows how much the forest relies on each feature: we shuffle one "
        "feature and measure how much worse the predictions get. The drop can be larger than 1, "
        "because a model that has lost its main input predicts worse than simply guessing the "
        "average, and its R² becomes negative.",
        "The scores and the feature importance were computed once for all R1 flights, so they "
        "do not change with the filters. The cells and the scatter plot follow the filters. "
        "The model leaves out the anemometer reading, because it measures the drone's own "
        "airspeed and would only repeat the speed. Some scatter remains that no model can "
        "explain, because flights with the same setting still differ by about 15 W (weather, "
        "battery and measurement noise).",
        "Only the R1 flights of the experiment are used, because the model was trained on them.",
    ),
    author=AUTHOR,
)

HEATMAP_VIEWS = {
    "Measured cruise power": "observed",
    "Random Forest prediction": "rf",
    "Difference: measured − Random Forest": "rf_gap",
    "Difference: measured − linear model": "lin_gap",
}

GROUP_OPTIONS = {"Altitude": "altitude", "Speed": "speed", "Payload": "payload", "Route": "route"}
LAYOUT_OPTIONS = {"Treemap": "treemap", "Icicle": "icicle", "Sunburst": "sunburst"}
ORDER_OPTIONS = {
    "Payload → altitude → speed": ("payload", "altitude", "speed"),
    "Altitude → speed → payload": ("altitude", "speed", "payload"),
    "Speed → altitude → payload": ("speed", "altitude", "payload"),
}


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
    tree_card(flights)
    ml_payload = tables.get("ml_payload")
    if ml_payload is not None:
        heatmap_card(flights, ml_payload)


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


@st.fragment
def tree_card(flights: pd.DataFrame) -> None:
    with chart_card(TREE) as card:
        col1, col2, _ = st.columns([1, 1, 1])
        layout = LAYOUT_OPTIONS[col1.selectbox("Drawing", list(LAYOUT_OPTIONS), key="tree_layout")]
        order_label = col2.selectbox("Order of levels", list(ORDER_OPTIONS), key="tree_order")
        order = ORDER_OPTIONS[order_label]
        # A new order builds a different tree; a fresh element also resets any zoom.
        card.plot(
            build_treemap(flights, order, layout), key=f"tree_chart_{layout}_{'_'.join(order)}"
        )
        card.finding = describe_treemap(flights, order)


@st.cache_data(show_spinner=False)
def _ml_metrics() -> dict:
    return loader.load_ml_metrics()


@st.fragment
def heatmap_card(flights: pd.DataFrame, ml_payload: pd.DataFrame) -> None:
    with chart_card(HEATMAP) as card:
        metrics = _ml_metrics()
        scores = model_scores(metrics)
        if scores:
            c1, c2, c3 = st.columns(3)
            c1.metric(
                "Random Forest R²",
                scores["rf"],
                help=f"Share of the flight-to-flight differences the model explains (1 = all). "
                f"Mean error {scores['rf_mae']}.",
            )
            c2.metric(
                "Linear model R²",
                scores["lin"],
                help=f"The same score for a straight-line model. Mean error {scores['lin_mae']}.",
            )
            c3.metric(
                "R² on unseen settings",
                scores["unseen"],
                help="Random Forest / linear model, when every flight of a setting is left out "
                "together, so the model has never seen that payload, speed and altitude.",
            )
            st.caption("These scores are for all R1 flights and do not follow the filters.")
        else:
            st.caption("Model scores are not available yet.")

        col, _ = st.columns([1, 1])
        label = col.selectbox("Show", list(HEATMAP_VIEWS), key="heatmap_view")
        view = HEATMAP_VIEWS[label]
        card.plot(build_payload_heatmap(flights, ml_payload, view), key="heatmap_chart")

        left, right = st.columns(2)
        with left:
            model = "linear" if view == "lin_gap" else "rf"
            card.plot(build_prediction_scatter(flights, ml_payload, model), key="heatmap_scatter")
        with right:
            card.plot(build_importance(metrics), key="heatmap_importance")
        card.finding = describe_payload_heatmap(flights, ml_payload, view)
