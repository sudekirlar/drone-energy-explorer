"""Flight & Temporal Analysis section: map, space-time cube, timeline (owner: Data).

The three cards are linked (E2): flights chosen on the map can be sent to the 3D view and to
the timeline through the session-state keys in docs/interfaces.md.
"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd
import streamlit as st

from src.charts.route_map import METRICS, build_route_map, metric_range
from src.charts.space_time_cube import build_space_time_cube
from src.charts.timeline import build_timeline
from src.sections.common import CardInfo, chart_card

AUTHOR = "İlayda Demir"

MAP = CardInfo(
    title="Power changes along the route only when the drone flies fast.",
    how_to_read=(
        "Each dot is one second of the flight, coloured by the measure you choose. "
        "The dark dot (H) is the take-off point and the white rings are the estimated waypoints."
    ),
    data=(
        "Every flight that passes the sidebar filters. Tick 'Include R2–R7' to see the other "
        "routes."
    ),
    finding=(
        "At 4 m/s (flight 8) the three legs draw almost the same power. At 12 m/s (flight 77) "
        "the drone slows below 1 m/s at each waypoint, so the colour changes at the corners."
    ),
    why=(
        "The routes were flown over real ground, so a map is the most natural way to show where "
        "the drone was and where it used energy."
    ),
    encoding=(
        "Position shows where the drone was. Colour shows the chosen measure on one sequential "
        "scale (Viridis), shared by both maps. The dark dot and the white rings mark the plan: "
        "the take-off point and the waypoints."
    ),
    interaction=(
        "Choose a route and two of its flights (select). Change the colour measure (encode). "
        "Zoom and pan (explore), and hover for details. Send the flights to the 3D view or the "
        "timeline (connect)."
    ),
    lecture=(
        "Lecture 7, trajectories. Minard's map of Napoleon's campaign draws a path on a map and "
        "shows a quantity along it; here the quantity is power instead of the army's size."
    ),
    author=AUTHOR,
)

CUBE = CardInfo(
    title="The 3D view shows the time and altitude that the map hides.",
    how_to_read=(
        "The floor is the map, in metres east and north. Height is time since take-off or "
        "altitude. A steep line means a slow flight; a vertical piece means the drone stood still."
    ),
    data=(
        "Up to four flights from any route. By default: R7 flight 278 and two R1 flights at 4 and "
        "12 m/s (flights 8 and 77)."
    ),
    finding=(
        "Flight 8 (4 m/s) climbs the time axis slowly and lasts about 160 s; flight 77 (12 m/s) "
        "takes about 100 s and pauses at each waypoint. On the altitude axis, flight 278 on R7 "
        "climbs in steps from 25 m to about 94 m."
    ),
    why=(
        "A map loses two real dimensions: time and altitude. A space-time cube shows both, which "
        "is worth the cost of 3D here."
    ),
    encoding=(
        "Position on the floor is position on the map. Height is time since take-off or "
        "altitude. Colour is the estimated phase by default, with the same colours as the map and "
        "the timeline."
    ),
    interaction=(
        "Rotate the cube (reconfigure). Switch the vertical axis or the colour (encode). Pick up "
        "to four flights (select), or bring them from the map (connect)."
    ),
    lecture=(
        "Lecture 7, space-time cubes: Hägerstrand's idea as presented by Kraak (2003). The lecture "
        "also lists the costs of 3D (hidden lines, distorted lengths), so the view shows at most "
        "four flights and starts from a fixed angle."
    ),
    author=AUTHOR,
)

TIMELINE = CardInfo(
    title="Inside one flight, the estimated phases match the changes in power, speed and altitude.",
    how_to_read=(
        "Four panels share one time axis: power, speed, altitude and battery voltage. Coloured "
        "bands show the estimated phases, and dotted lines mark the waypoint turns."
    ),
    data=(
        "One flight from any route. By default: R1 flight 77 (12 m/s, 0 g, 25 m), where every "
        "phase is easy to see."
    ),
    finding=(
        "In flight 77 the drone slows below 1 m/s at every waypoint. The battery voltage falls "
        "from 24.5 V to about 21.4 V during the flight but returns to 24.2 V after landing, so "
        "most of the drop is a temporary sag under load, not a discharged battery."
    ),
    why=(
        "The other charts give each flight one number. This chart looks inside a single flight, "
        "and it lets us check the estimated phases by eye."
    ),
    encoding=(
        "Time runs from left to right. Each measure has its own panel and unit, instead of two "
        "y-axes on one chart. The background colour shows the estimated phase."
    ),
    interaction=(
        "Pick a flight (select), or open one from the map (connect). Zoom into one panel and the "
        "others follow (explore). Hover to see all four values at the same moment. Turn the phase "
        "bands on or off (encode)."
    ),
    lecture=(
        "Lecture 7, time series: the most direct way to follow a change over time. Small panels "
        "replace a misleading second y-axis."
    ),
    author=AUTHOR,
)


def _flight_label(flights: pd.DataFrame) -> Callable[[int], str]:
    """'77 · 12 m/s, 0 g, 25 m', so a visitor knows what each flight number means."""
    info = flights.set_index("flight")

    def label(flight: int | None) -> str:
        if flight is None:
            return "None"
        row = info.loc[flight]
        altitude = "stepped" if pd.isna(row["altitude_m"]) else f"{row['altitude_m']:.0f} m"
        return f"{flight} · {row['speed_mps']} m/s, {row['payload_g']} g, {altitude}"

    return label


def _keep_valid(key: str, options: list, fallback) -> None:
    """Repair a widget's stored value before it is drawn (filters can remove options)."""
    if st.session_state.get(key) not in options:
        st.session_state[key] = fallback


def render(tables: dict[str, pd.DataFrame]) -> None:
    st.markdown("### Flight & Temporal Analysis")
    st.caption(
        "Where, when and how the drone flew. The three charts are linked: send flights from the "
        "map to the 3D view or to the timeline."
    )
    flights = tables.get("flights")
    telemetry = tables.get("telemetry_1hz")
    if flights is None or telemetry is None or flights.empty or telemetry.empty:
        st.info("No flights match the current filters.")
        return

    valid = set(telemetry["flight"].unique())
    all_ids = sorted(int(f) for f in flights["flight"] if f in valid)
    if not all_ids:
        st.warning("No telemetry matches the current filters.")
        return

    st.session_state.setdefault("map_flights", [])
    st.session_state.setdefault("cube_flights", [278, 8, 77])  # defaults from interfaces.md
    st.session_state.setdefault("timeline_flight", 77)
    label = _flight_label(flights)

    map_card(flights, telemetry, tables.get("waypoints"), all_ids, label)
    cube_card(telemetry, all_ids, label)
    timeline_card(telemetry, all_ids, label)


@st.fragment
def map_card(flights, telemetry, waypoints, all_ids, label) -> None:
    with chart_card(MAP) as card:
        routes = sorted(flights.loc[flights["flight"].isin(all_ids), "route"].unique())
        cols = st.columns([1, 2, 2, 2])
        _keep_valid("map_route_select", routes, routes[0])
        route = cols[0].selectbox("Route", routes, key="map_route_select")
        route_ids = [
            f for f in all_ids if f in set(flights.loc[flights["route"] == route, "flight"])
        ]
        _keep_valid("map_flight_a", route_ids, route_ids[0])
        a = cols[1].selectbox("Flight A", route_ids, format_func=label, key="map_flight_a")
        b_options = [None] + [f for f in route_ids if f != a]
        _keep_valid("map_flight_b", b_options, None)
        b = cols[2].selectbox(
            "Flight B (optional)", b_options, format_func=label, key="map_flight_b"
        )
        color_by = cols[3].selectbox("Colour by", list(METRICS), key="map_color")

        selected = [a] + ([b] if b is not None else [])
        st.session_state["map_flights"] = selected
        shared_range = metric_range(telemetry, selected, color_by)
        for column, flight, slot in zip(st.columns(len(selected)), selected, "ab", strict=False):
            with column:
                card.plot(
                    build_route_map(
                        telemetry, waypoints, [flight], color_by, shared_range, label(flight)
                    ),
                    key=f"map_chart_{slot}",
                )

        buttons = st.columns(3)
        if buttons[0].button("Send these flights to the 3D view", key="map_to_cube"):
            st.session_state["cube_flights"] = selected
            st.session_state["cube_select_flights"] = selected
            st.rerun()
        for column, flight, name in zip(buttons[1:], selected, "AB", strict=False):
            if column.button(f"Open flight {name} in the timeline", key=f"map_to_timeline_{name}"):
                st.session_state["timeline_flight"] = flight
                st.session_state["timeline_select"] = flight
                st.rerun()


@st.fragment
def cube_card(telemetry, all_ids, label) -> None:
    with chart_card(CUBE) as card:
        current = st.session_state.get("cube_select_flights", st.session_state["cube_flights"])
        current = [f for f in current if f in all_ids][:4]
        if not current:
            current = [f for f in [278, 8, 77] if f in all_ids][:4] or all_ids[:2]
        st.session_state["cube_select_flights"] = current
        choices = st.multiselect(
            "Flights (up to four)",
            all_ids,
            max_selections=4,
            format_func=label,
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
            index=3,  # chart guide: phase by default, same colours as the map and the timeline
            key="cube_color_by",
        )
        if choices:
            card.plot(build_space_time_cube(telemetry, choices, z_axis, color), key="cube_plot")
        else:
            st.info("Choose at least one flight.")


@st.fragment
def timeline_card(telemetry, all_ids, label) -> None:
    with chart_card(TIMELINE) as card:
        current = st.session_state.get("timeline_select", st.session_state["timeline_flight"])
        st.session_state["timeline_select"] = current if current in all_ids else all_ids[0]
        col1, col2 = st.columns([3, 1])
        flight = col1.selectbox("Flight", all_ids, format_func=label, key="timeline_select")
        st.session_state["timeline_flight"] = flight
        show = col2.checkbox("Show estimated phases", value=True, key="timeline_show_phase")
        card.plot(build_timeline(telemetry, flight, show), key="timeline_plot")
