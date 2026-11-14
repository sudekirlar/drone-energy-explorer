"""Multivariate and ML section (owner: uiml)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.charts.pcp import build_pcp
from src.charts.splom import build_splom
from src.charts.violin import (
    build_phase_payload_violin,
    compute_phase_payload_power,
    summarize_payload_effect,
)
from src.ml.clustering import run_kmeans
from src.sections.common import CardInfo, chart_card


@st.cache_data(show_spinner=False)
def _cached_kmeans(flights: pd.DataFrame, k: int):
    return run_kmeans(flights, k=k)


@st.cache_data(show_spinner=False)
def _cached_phase_power(telemetry: pd.DataFrame, flights: pd.DataFrame) -> pd.DataFrame:
    return compute_phase_payload_power(telemetry, flights)


def _build_violin_finding(phase_power: pd.DataFrame) -> str:
    """Compute a data-driven finding sentence from active phase x payload power values."""
    if phase_power.empty:
        return "No flight phase power observations match the current filter selection."

    stats = summarize_payload_effect(phase_power)
    by_phase = phase_power.groupby("phase")["mean_power_w"].mean().sort_values()
    low_phase, low_w = str(by_phase.index[0]), float(by_phase.iloc[0])
    high_phase, high_w = str(by_phase.index[-1]), float(by_phase.iloc[-1])

    return (
        f"Each +250 g payload step adds {stats['delta_w']:.1f} W (~{stats['delta_pct']:.1f}%) "
        f"on average across all four flight phases ({stats['cruise_delta_w']:.1f} W or "
        f"{stats['cruise_delta_pct']:.1f}% in cruise), while baseline power shifts from "
        f"{low_phase} ({low_w:.0f} W) to {high_phase} ({high_w:.0f} W)."
    )


def _build_pcp_finding(summary: pd.DataFrame, silhouette: float) -> str:
    """Build a data-driven finding sentence from cluster_summary and silhouette score."""
    ordered = summary.sort_values("mean_energy_wh", ascending=True).reset_index(drop=True)
    low = ordered.iloc[0]
    high = ordered.iloc[-1]
    k = len(ordered)

    base = (
        f"Group 1 ({int(low['n_flights'])} flights) uses {low['mean_energy_wh']:.1f} Wh on average "
        f"and Group {k} ({int(high['n_flights'])} flights) uses {high['mean_energy_wh']:.1f} Wh."
    )

    detail = ""
    if k >= 3:
        prev = ordered.iloc[-2]
        power_diff = abs(high["mean_cruise_power_w"] - prev["mean_cruise_power_w"])
        if power_diff <= 15.0:
            detail = (
                f" Groups {k - 1} and {k} have almost the same cruise power "
                f"({prev['mean_cruise_power_w']:.0f} W and {high['mean_cruise_power_w']:.0f} W); "
                f"Group {k} uses more energy because its flights last longer "
                f"({high['mean_duration_s']:.0f} s against {prev['mean_duration_s']:.0f} s)."
            )
        else:
            detail = (
                f" Group {k} draws {high['mean_cruise_power_w']:.0f} W in cruise against "
                f"{prev['mean_cruise_power_w']:.0f} W in Group {k - 1}."
            )

    overlap_note = (
        f" The silhouette score of {silhouette:.2f} means that the groups overlap "
        "rather than forming hard categories."
    )
    return base + detail + overlap_note


def _build_splom_finding(flights: pd.DataFrame) -> str:
    """Compute a pairwise relationship finding from the active flights table."""
    if flights.empty:
        return "No flights match the current filter selection."

    parts: list[str] = []

    if {"cruise_power_w", "climb_power_w"}.issubset(flights.columns):
        pair_pow = flights[["cruise_power_w", "climb_power_w"]].dropna()
        if (
            len(pair_pow) >= 3
            and pair_pow["cruise_power_w"].std() > 0
            and pair_pow["climb_power_w"].std() > 0
        ):
            r_pow = float(pair_pow["cruise_power_w"].corr(pair_pow["climb_power_w"]))
            parts.append(
                f"Cruise power and climb power rise together across flights (r = {r_pow:.2f})."
            )

    if {"speed_mps", "wh_per_km"}.issubset(flights.columns):
        pair_spd = flights[["speed_mps", "wh_per_km"]].dropna()
        by_speed_wh = pair_spd.groupby("speed_mps")["wh_per_km"].median().sort_index()
        if (
            len(by_speed_wh) >= 2
            and len(pair_spd) >= 3
            and pair_spd["speed_mps"].std() > 0
            and pair_spd["wh_per_km"].std() > 0
        ):
            r_spd = float(pair_spd["speed_mps"].corr(pair_spd["wh_per_km"]))
            s_min, s_max = by_speed_wh.index[0], by_speed_wh.index[-1]
            parts.append(
                f"Speed vs Wh/km drops from {by_speed_wh.iloc[0]:.1f} Wh/km at "
                f"{s_min:g} m/s to {by_speed_wh.iloc[-1]:.1f} Wh/km at {s_max:g} m/s along a "
                f"curved trend, so linear correlation (r = {r_spd:.2f}) understates it."
            )
        elif len(by_speed_wh) == 1:
            s_only = by_speed_wh.index[0]
            parts.append(
                f"At {s_only:g} m/s, median energy per kilometre is "
                f"{by_speed_wh.iloc[0]:.1f} Wh/km."
            )

    return " ".join(parts) if parts else "Pairwise flight telemetry relationships are shown above."


def render_multivariate_ml(flights: pd.DataFrame, telemetry: pd.DataFrame) -> None:
    """Render the Parallel Coordinates Plot and Scatterplot Matrix cards."""
    design_flights = (
        flights.loc[flights["in_design"]].reset_index(drop=True)
        if "in_design" in flights.columns
        else flights.reset_index(drop=True)
    )

    pcp_info = CardInfo(
        title="Flight groups",
        how_to_read=(
            "Each polyline is one experimental flight across nine telemetry measures and its "
            "K-means group. Drag any axis label left or right to reorder dimensions, or drag "
            "vertically along an axis to brush a subset of flights."
        ),
        about=(
            "This view groups the R1 design flights (181 flights in the default view) using "
            "K-means clustering on standardized energy, Wh/km, duration, cruise power, and "
            "climb power; payload is not used as a clustering feature, and the anemometer "
            "channel is excluded.",
            "Groups are ordered from lowest to highest mean energy consumption so that Group 1 "
            "always denotes the lowest-energy flights for the chosen k.",
        ),
        author="Pelin G?l K?z?lk?l??",
    )

    cluster_labels: pd.Series | None = None

    with chart_card(pcp_info) as card:
        col_slider, col_metric = st.columns([3, 1])
        with col_slider:
            k = st.slider(
                "Number of K-means clusters (k)",
                min_value=2,
                max_value=6,
                value=3,
                step=1,
                key="kmeans_k",
            )

        if len(design_flights) < k:
            st.warning("Not enough filtered flights to form the requested number of clusters.")
        else:
            result = _cached_kmeans(design_flights, k=k)
            cluster_labels = result.labels
            with col_metric:
                st.metric("Silhouette score", f"{result.silhouette:.3f}")

            fig_pcp = build_pcp(design_flights, result.labels)
            card.plot(fig_pcp, key="pcp_chart")
            card.finding = _build_pcp_finding(result.cluster_summary, result.silhouette)

    splom_info = CardInfo(
        title="Pairs of flight measures",
        how_to_read=(
            "Each lower-triangle cell plots two flight telemetry variables against each other, "
            "with the diagonal and upper triangle hidden to avoid duplicate views. Drag a box "
            "in any panel to highlight the same flights across every other panel."
        ),
        about=(
            "Total energy (Wh) is omitted on purpose because it scales directly with route length "
            "and energy per kilometre, while the anemometer channel is left out (D3).",
            "Use the colour selector to compare payload mass, cruise altitude, or the K-means "
            "groups produced using the k slider in the chart above.",
        ),
        author="Pelin G?l K?z?lk?l??",
    )

    with chart_card(splom_info) as splom_card:
        color_options = {
            "Payload": "payload",
            "K-means cluster": "cluster",
            "Altitude": "altitude",
        }
        selected_label = st.selectbox(
            "Colour flights by",
            options=list(color_options.keys()),
            index=0,
            key="splom_color_by",
        )
        color_mode = color_options[selected_label]

        if color_mode == "cluster" and cluster_labels is None:
            st.warning("Cluster labels are unavailable for the current filter selection.")
            return

        fig_splom = build_splom(
            design_flights,
            color_by=color_mode,
            labels=cluster_labels,
        )
        splom_card.plot(fig_splom, key="splom_chart")
        splom_card.finding = _build_splom_finding(design_flights)

    violin_info = CardInfo(
        title="Power by phase and payload",
        how_to_read=(
            "Each violin shows the distribution of per-flight mean electrical power across the "
            "four active flight phases, shaded from light to dark blue for 0 g, 250 g, and 500 g "
            "payloads. Horizontal bars inside each violin mark the median and interquartile range."
        ),
        about=(
            "Mean power (W) is aggregated per flight within Take-off, Cruise, Manoeuvre, and "
            "Landing on the R1 design flights (181 flights in the default view), excluding Ground.",
            "Use the checkbox to overlay individual flight averages on top of the kernel density.",
        ),
        author="Pelin Gül Kızılkılıç",
    )

    with chart_card(violin_info) as violin_card:
        show_points = st.checkbox(
            "Show flight points",
            value=False,
            key="violin_show_points",
        )

        phase_power = _cached_phase_power(telemetry, design_flights)
        fig_violin = build_phase_payload_violin(
            phase_power,
            show_points=show_points,
            cut_y_axis=True,
        )
        violin_card.plot(fig_violin, key="violin_chart")
        violin_card.finding = _build_violin_finding(phase_power)


def render(tables: dict[str, pd.DataFrame], filters: Any = None) -> None:
    """Entry point called by app.py section router."""
    st.markdown("### Multivariate Analysis & ML")
    st.caption(
        "How flight variables cluster together and how power varies across operating conditions."
    )
    flights = tables.get("flights", pd.DataFrame())
    telemetry = tables.get("telemetry_1hz", pd.DataFrame())
    render_multivariate_ml(flights, telemetry)
