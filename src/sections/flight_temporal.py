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
LEGS = ("Straight leg", "Sloped cruise")

MAP = CardInfo(
    title="Flight routes",
    how_to_read=(
        "Each dot is one second of a flight, and its colour shows the measure you choose. "
        "The black dot marks the take-off point, and the white rings mark the estimated "
        "waypoints."
    ),
    about=(
        "This map shows the route that each flight really flew, in the same way that a ground "
        "station such as Mission Planner shows a drone's track over the ground. It lets you check "
        "that the drone followed its planned route and see where on that route it used more "
        "power.",
        "Each dot sits at the drone's real GPS position. Both maps use one sequential colour "
        "scale (Viridis), so the same colour means the same value in flight A and in flight B. "
        "When you put a slow flight next to a fast flight on the same route, you can see how "
        "speed changes the power along the path.",
        "You can choose a route and two of its flights, change the colour measure, zoom, pan and "
        "hover over a dot to read its values. The buttons under the maps send the flights to the "
        "3D view or to the timeline.",
        "The idea comes from Lecture 7 on trajectories. There, Minard's map of Napoleon's "
        "campaign draws a path on a map and shows a quantity along it.",
        "The map uses every flight that passes the sidebar filters. Tick 'Include R2–R7' in the "
        "sidebar to see the routes other than R1.",
    ),
    author=AUTHOR,
)

CUBE = CardInfo(
    title="Space–time cube",
    how_to_read=(
        "The floor of the cube is the map, and the height is the time since take-off or the "
        "altitude. A steep line means a slow flight, and a vertical line means that the drone "
        "stood still."
    ),
    about=(
        "A map cannot show when the drone was at a place or how high it flew. This 3D view adds "
        "the missing dimension, so you can compare the pace of different flights and see how "
        "they climbed.",
        "With time as the height, a fast flight draws a short and flat line, and a slow flight "
        "draws a tall and steep one. With altitude as the height, you can see the vertical climb "
        "at take-off and the stepped climb on route R7. By default the colour shows the "
        "estimated phase, with the same colours as the map and the timeline.",
        "You can rotate the cube, switch the height between time and altitude, change the colour "
        "and choose up to four flights. Flights that you send from the map appear here.",
        "The space–time cube comes from Lecture 7, which presents the idea of Hägerstrand and "
        "Kraak. The lecture also warns about the costs of 3D, such as lines that hide each "
        "other. For this reason the view shows at most four flights and starts from a fixed "
        "angle.",
        "By default the cube shows flight 278 on route R7 and flights 8 and 77 on route R1, "
        "which fly at 4 m/s and 12 m/s.",
    ),
    author=AUTHOR,
)

TIMELINE = CardInfo(
    title="Inside one flight",
    how_to_read=(
        "The four panels share one time axis and show power, speed, altitude and battery "
        "voltage. The coloured bands show the estimated phases, and the dotted lines mark the "
        "waypoint turns."
    ),
    about=(
        "The other charts describe each flight with a few numbers. This chart looks inside a "
        "single flight and shows how its measures change together from take-off to landing.",
        "It also lets us check the estimated phases by eye. Each phase band should begin where "
        "the power, the speed or the altitude changes.",
        "Each measure has its own panel and its own unit, because two units on one chart with "
        "two y-axes can mislead the reader. Time runs from left to right, as in the time series "
        "of the lectures. The speed panel also shows the anemometer, which measures the drone's "
        "airspeed and not the wind.",
        "You can choose a flight, zoom into one panel while the others follow, hover to read all "
        "four values at the same moment, and turn the phase bands on or off.",
    ),
    author=AUTHOR,
)


def _join(items: list[str]) -> str:
    """'a', 'a and b', 'a, b and c'."""
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _airborne(rows: pd.DataFrame) -> pd.DataFrame:
    return rows.loc[rows["phase"] != "Ground"] if "phase" in rows else rows


def describe_map(telemetry: pd.DataFrame, flight_ids: list[int], label) -> str | None:
    """Power on the straight legs and in the waypoint turns of the flights on screen."""
    if "sub_phase" not in telemetry:
        return None
    sentences = []
    for flight in flight_ids:
        rows = telemetry.loc[telemetry["flight"] == flight]
        leg = rows.loc[rows["sub_phase"].isin(LEGS), "power_w"].mean()
        turn = rows.loc[rows["sub_phase"] == "WP turn", "power_w"].mean()
        if pd.isna(leg):
            continue
        name = f"Flight {flight} ({label(flight).split(' · ')[1].split(',')[0]})"
        if pd.isna(turn):
            sentences.append(f"{name} uses about {leg:.0f} W on its straight legs.")
        else:
            sentences.append(
                f"{name} uses about {leg:.0f} W on its straight legs and {turn:.0f} W in its "
                "waypoint turns."
            )
    return " ".join(sentences) or None


def describe_cube(telemetry: pd.DataFrame, flight_ids: list[int], z_axis: str) -> str | None:
    """Time in the air, or highest altitude, of the flights on screen."""
    if z_axis == "Time (s)" and "t_since_takeoff_s" not in telemetry:
        return None
    parts = []
    for flight in flight_ids:
        rows = _airborne(telemetry.loc[telemetry["flight"] == flight])
        if rows.empty:
            continue
        if z_axis == "Time (s)" and "t_since_takeoff_s" in rows:
            seconds = rows["t_since_takeoff_s"].max() - max(rows["t_since_takeoff_s"].min(), 0)
            parts.append((flight, f"{seconds:.0f} s"))
        else:
            parts.append((flight, f"{rows['alt_rel_m'].max():.0f} m"))
    if not parts:
        return None
    if z_axis == "Time (s)":
        first, rest = parts[0], parts[1:]
        text = f"Flight {first[0]} is in the air for about {first[1]}"
        tail = [f"flight {f} for about {v}" for f, v in rest]
    else:
        first, rest = parts[0], parts[1:]
        text = f"Flight {first[0]} climbs to about {first[1]}"
        tail = [f"flight {f} to about {v}" for f, v in rest]
    return _join([text, *tail]) + "."


def describe_timeline(telemetry: pd.DataFrame, flight: int) -> str | None:
    """Waypoint turns and the voltage sag of the flight on screen."""
    rows = telemetry.loc[telemetry["flight"] == flight].sort_values("t_s")
    if rows.empty or "phase" not in rows:
        return None
    sentences = []
    if "sub_phase" in rows:
        in_turn = rows["sub_phase"].eq("WP turn")
        turns = int((in_turn & ~in_turn.shift(fill_value=False)).sum())
        if turns:
            slowest = rows.loc[in_turn, "ground_speed_mps"].min()
            word = "turn" if turns == 1 else "turns"
            sentences.append(
                f"Flight {flight} makes {turns} waypoint {word} and slows down to "
                f"{slowest:.1f} m/s in them."
            )
    air = _airborne(rows)
    before = (
        rows.loc[rows["t_since_takeoff_s"] < 0, "voltage_v"] if "t_since_takeoff_s" in rows else []
    )
    if len(air) and len(before):
        subject = "Its battery voltage" if sentences else f"The battery voltage of flight {flight}"
        sentences.append(
            f"{subject} drops from {before.iloc[:5].median():.1f} V before take-off "
            f"to {air['voltage_v'].min():.1f} V in the air, and it is back at "
            f"{rows['voltage_v'].iloc[-5:].median():.1f} V after landing."
        )
    return " ".join(sentences) or None


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
        card.finding = describe_map(telemetry, selected, label)

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
            card.finding = describe_cube(telemetry, choices, z_axis)
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
        card.finding = describe_timeline(telemetry, flight)
