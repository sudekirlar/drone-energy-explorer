"""Flight & Temporal Analysis section: maps, cube, timeline (Data owner)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.charts.route_map import METRICS, build_route_map
from src.charts.space_time_cube import build_space_time_cube
from src.charts.timeline import build_timeline


def _flight_options(flights: pd.DataFrame) -> list[int]:
    return sorted(int(v) for v in flights["flight"].dropna().unique())


def render(tables: dict[str, pd.DataFrame]) -> None:
    st.markdown("### Flight & Temporal Analysis")
    st.caption("Geography → space–time → telemetry. All views use the current sidebar filters.")
    flights = tables.get("flights")
    telemetry = tables.get("telemetry_1hz")
    if flights is None or telemetry is None or flights.empty or telemetry.empty:
        st.info("Flight charts need `flights` and `telemetry_1hz` contract tables.")
        return

    valid = set(telemetry["flight"].unique())
    all_ids = [f for f in _flight_options(flights) if f in valid]
    if not all_ids:
        st.warning("No telemetry matches the active filters.")
        return

    st.session_state.setdefault("map_flights", [])
    st.session_state.setdefault("cube_flights", [])
    st.session_state.setdefault("timeline_flight", 77)
    waypoints = tables.get("waypoints")

    with st.container(border=True):
        st.markdown("#### G1 · Where did the drone fly?")
        st.caption(
            "Line = flight trajectory; points = selected measurement. H marks take-off; "
            "WP markers come from Platform phase detection when available."
        )
        routes = sorted(flights["route"].dropna().unique().tolist())
        route = st.selectbox("Route", routes, key="map_route_select")
        by_route = flights.loc[flights["route"] == route, "flight"]
        route_ids = [int(v) for v in by_route if v in valid]
        st.caption(f"{len(route_ids)} flights available in {route} after sidebar filtering.")
        if not route_ids:
            st.info("No flights in this route for the current filters.")
        else:
            cols = st.columns([2, 2, 2])
            a = cols[0].selectbox("Flight A", route_ids, key="map_flight_a")
            second_choices = [None] + [v for v in route_ids if v != a]
            b = cols[1].selectbox(
                "Flight B (optional)",
                second_choices,
                format_func=lambda x: "None" if x is None else str(x),
                key="map_flight_b",
            )
            color_by = cols[2].selectbox("Colour by", list(METRICS), key="map_color")
            selected = [a] + ([b] if b is not None else [])
            st.session_state["map_flights"] = selected
            st.plotly_chart(
                build_route_map(telemetry, waypoints, selected, color_by),
                use_container_width=True,
                key="map_chart",
            )
            st.info(
                "**Finding:** Use two flights from the same route to compare where "
                "power, ground speed or altitude changes along the path."
            )
            btn = st.columns(2)
            if btn[0].button("Send selected flights to 3D", key="map_to_cube"):
                st.session_state["cube_flights"] = selected
                st.session_state["cube_select_flights"] = selected
                st.rerun()
            if btn[1].button("Open flight A in timeline", key="map_to_timeline"):
                st.session_state["timeline_flight"] = a
                st.session_state["timeline_select"] = a
                st.rerun()
            with st.expander("About the map"):
                st.caption(
                    "Lecture: geographical visualization · Interaction: filter, "
                    "compare, reconfigure, connect · Author: Data role"
                )

    with st.container(border=True):
        st.markdown("#### G2 · How does the flight evolve through space and time?")
        st.caption(
            "X/Y are metres east/north of the R1 reference point; Z is elapsed "
            "recording time or relative altitude. Compare at most four flights."
        )
        defaults = [v for v in st.session_state["cube_flights"] if v in all_ids][:4]
        if not defaults:
            defaults = [v for v in [278, 8, 77] if v in all_ids][:4]
        if not defaults:
            defaults = all_ids[:2]
        choices = st.multiselect(
            "Flights (max 4)",
            all_ids,
            default=defaults,
            max_selections=4,
            key="cube_select_flights",
        )
        st.session_state["cube_flights"] = choices
        col1, col2 = st.columns(2)
        z_axis = col1.selectbox(
            "Vertical axis", ["Time (s)", "Relative altitude (m)"], key="cube_z_axis"
        )
        color = col2.selectbox(
            "Colour by",
            ["Flight", "Power (W)", "Relative altitude (m)", "Estimated phase"],
            key="cube_color_by",
        )
        if choices:
            st.plotly_chart(
                build_space_time_cube(telemetry, choices, z_axis, color),
                use_container_width=True,
                key="cube_plot",
            )
            st.info(
                "**How to read:** The time axis exposes flight duration and speed; "
                "the altitude axis exposes the climb profile. Rotate to compare trajectories."
            )
        else:
            st.info("Choose at least one flight.")
        with st.expander("About the cube"):
            st.caption(
                "Lecture: advanced multivariate and temporal visualization · "
                "Interaction: rotate, select, reconfigure · Author: Data role"
            )

    with st.container(border=True):
        st.markdown("#### G3 · What happens inside a flight?")
        st.caption(
            "Four synchronized panels; the shaded bands are Platform-estimated "
            "phases when available, not ground-truth labels."
        )
        preferred = st.session_state["timeline_flight"]
        initial = all_ids.index(preferred) if preferred in all_ids else 0
        flight = st.selectbox("Flight", all_ids, index=initial, key="timeline_select")
        st.session_state["timeline_flight"] = flight
        show = st.checkbox("Show estimated phase bands", value=True, key="timeline_show_phase")
        data_for_flight = telemetry.loc[telemetry["flight"] == flight]
        if "phase" not in data_for_flight or data_for_flight["phase"].isna().all():
            st.caption("Estimated phases are not available yet; telemetry is shown without bands.")
        st.plotly_chart(
            build_timeline(telemetry, flight, show),
            use_container_width=True,
            key="timeline_plot",
        )
        st.info(
            "**Finding:** Compare brief power peaks, horizontal movement, "
            "vertical movement and voltage changes at the same timestamp."
        )
        with st.expander("About the timeline"):
            st.caption(
                "Lecture: temporal visualization · Interaction: unified hover, "
                "single-flight selection, connect · Author: Data role"
            )
