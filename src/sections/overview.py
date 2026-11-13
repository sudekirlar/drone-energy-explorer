"""Overview: the landing page, followed by how the data was prepared (owner: Data, E1).

The top of the page tells a first-time visitor what the dashboard is about and where to go.
The data quality evidence (assignment item 1) sits underneath in folded boxes.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data.schema import data_dictionary

REPO_URL = "https://github.com/sudekirlar/drone-energy-explorer"
DATA_DOI = "https://doi.org/10.1184/R1/12683453"

# (menu name, question, charts, author). Menu names must match the sections in app.py.
SECTIONS = [
    (
        "Flight & Temporal",
        "Where, when and how did the drone fly?",
        "A route map, a space–time cube and a timeline of one flight.",
        "İlayda Demir",
    ),
    (
        "Energy & Conditions",
        "Where does the energy go, and how do payload, speed and altitude change it?",
        "An energy budget (Sankey), a tree of the experiment and a payload–speed heat map "
        "with a Random Forest model.",
        "Sude Kırlar",
    ),
    (
        "Multivariate & ML",
        "Which flights are alike, and how are their measures related?",
        "Parallel coordinates with K-means groups, a scatterplot matrix, power by phase and "
        "payload, and all flights over time.",
        "Pelin Gül Kızılkılıç",
    ),
]

QUALITY_COLUMNS = {
    "rule_id": "Rule",
    "description": "What it does",
    "rows_affected": "Rows changed",
    "flights_affected": "Flights changed",
    "iso25012": "ISO/IEC 25012 characteristic",
}


def _hours_in_air(tables: dict[str, pd.DataFrame]) -> float:
    """Time outside the Ground phase; the recordings also include time on the ground."""
    energy = tables.get("phase_energy")
    if energy is None or energy.empty:
        return float(tables["flights"]["duration_s"].sum() / 3600)
    return float(energy.loc[energy["phase"] != "Ground", "duration_s"].sum() / 3600)


def _open_section(name: str) -> None:
    """Button callback: runs before the next rerun, so the menu can still be changed."""
    st.session_state["menu_section"] = name


def render(tables: dict[str, pd.DataFrame]) -> None:
    flights = tables["flights"]

    st.markdown("### Overview")
    st.markdown(
        "This dashboard explores how a delivery drone uses its battery. It is built on real "
        "flights of a DJI Matrice 100 quadcopter, which Carnegie Mellon University flew near "
        "Pittsburgh with packages of 0, 250 and 500 g."
    )
    st.info(
        "Our main question is how payload, cruise speed and altitude shape the energy that a "
        "delivery drone uses, and in which part of the flight that energy is spent."
    )

    if flights.empty:
        st.warning("No flights match the current filters.")
    else:
        cols = st.columns(4)
        cols[0].metric("Flights", f"{flights['flight'].nunique():,}")
        cols[1].metric("Time in the air", f"{_hours_in_air(tables):,.1f} h")
        cols[2].metric("Distance flown", f"{flights['distance_m'].sum() / 1000:,.1f} km")
        cols[3].metric("Median energy per flight", f"{flights['energy_wh'].median():,.1f} Wh")
        st.caption("These numbers follow the filters in the sidebar.")

    st.markdown("#### What you can explore")
    for column, (name, question, charts, author) in zip(
        st.columns(len(SECTIONS)), SECTIONS, strict=True
    ):
        with column, st.container(border=True):
            st.markdown(f"**{name}**")
            st.markdown(question)
            st.caption(f"{charts} Made by {author}.")
            st.button(
                "Open this section",
                key=f"overview_open_{name}",
                on_click=_open_section,
                args=(name,),
            )

    st.markdown("#### About the data")
    st.markdown(
        "The data set has 209 recordings. We use the 196 real flights on seven routes (R1–R7) "
        "and leave out the ground and hover tests. Most charts use route R1, which is a "
        "controlled experiment: the drone flies the same triangle every time, and only the "
        "payload (0, 250 or 500 g), the altitude (25 to 100 m) and the cruise speed (4 to "
        "12 m/s) change. This lets us compare flights fairly."
    )
    st.markdown(
        "The results describe one drone model in one place. They should not be applied to "
        "other drones, batteries or weather conditions without new data."
    )
    st.caption(
        f"Data: Rodrigues, T. A. et al. (2021), Carnegie Mellon University, "
        f"[{DATA_DOI}]({DATA_DOI}), CC BY 4.0. Code: [{REPO_URL}]({REPO_URL}). "
        "Made by Sude Kırlar, İlayda Demir and Pelin Gül Kızılkılıç for CEN445 Introduction to "
        "Data Visualization, Çukurova University, Fall 2026."
    )

    st.markdown("#### How we prepared the data")
    st.markdown(
        "Power is battery voltage times current, and energy is added up at the original "
        "sampling rate before the data is reduced to one row per second. The boxes below show "
        "every cleaning rule, the quality checks and the meaning of each column."
    )
    _quality_details(tables)


def _quality_details(tables: dict[str, pd.DataFrame]) -> None:
    quality = tables.get("quality_log")
    with st.expander("Cleaning rules and how many rows they changed"):
        if quality is None or quality.empty:
            st.warning("The cleaning log is not available for the current data.")
        else:
            st.dataframe(
                quality[list(QUALITY_COLUMNS)].rename(columns=QUALITY_COLUMNS),
                width="stretch",
                hide_index=True,
            )
            st.caption(
                "Outlier flights stay in the data. Tick 'Hide outlier flights' in the sidebar to "
                "leave them out of every chart."
            )

    with st.expander("Quality checks (ISO/IEC 25012)"):
        st.dataframe(
            pd.DataFrame(
                [
                    (
                        "Accuracy",
                        "Small negative current readings on the ground are set to zero. Four "
                        "start times with likely typing errors are corrected, and the original "
                        "values are kept.",
                    ),
                    ("Completeness", _completeness(tables["flights"])),
                    (
                        "Consistency",
                        "Route filtering and outlier flags follow written rules that are "
                        "applied in the same way to every flight.",
                    ),
                    (
                        "Credibility",
                        "Flight phases are estimated by a rule, because the data has no phase "
                        "labels. The checks below test that rule.",
                    ),
                    (
                        "Traceability",
                        "Corrected values keep their originals, and every rule is listed in the "
                        "cleaning log.",
                    ),
                ],
                columns=["Characteristic", "What we did"],
            ),
            width="stretch",
            hide_index=True,
        )
        for sentence in _phase_checks(tables):
            st.markdown(f"- {sentence}")
        st.markdown(
            "- Flights on different days do not use significantly different amounts of energy "
            "(Kruskal–Wallis test, p ≈ 0.09)."
        )

    with st.expander("Columns and units"):
        st.dataframe(pd.DataFrame(data_dictionary()), width="stretch", hide_index=True)


def _completeness(flights: pd.DataFrame) -> str:
    """Gaps in the recordings of the flights on screen."""
    with_gaps = int((flights["large_gap_count"] > 0).sum())
    return (
        "Readings arrive every 0.1 to 0.2 s. A gap longer than one second is counted for each "
        f"flight; {with_gaps} of the {len(flights)} flights shown here have at least one."
    )


def _phase_checks(tables: dict[str, pd.DataFrame]) -> list[str]:
    """Checks of the estimated phases, computed from the tables on screen."""
    flights, energy = tables["flights"], tables.get("phase_energy")
    if energy is None or energy.empty or flights.empty:
        return []
    totals = flights.set_index("flight")["energy_wh"]
    gap = (energy.groupby("flight")["energy_wh"].sum() - totals).abs().max()
    match = (
        "to within a millionth of a watt-hour"
        if gap < 1e-6
        else f"with a largest difference of {gap:.3f} Wh"
    )
    sentences = [f"The energy of the estimated phases adds up to each flight's total {match}."]
    design = flights.loc[flights["in_design"]]
    if len(design):
        two = int((design["wp_turn_count"] == 2).sum())
        sentences.append(
            f"{two} of the {len(design)} R1 experiment flights shown here have exactly the two "
            "waypoint turns of the planned triangle."
        )
    return sentences
