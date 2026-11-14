"""Grouped violin plot of power by flight phase and payload (owner: uiml)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.theme import PALETTES

MAIN_PHASES: tuple[str, ...] = ("Take-off", "Cruise", "Manoeuvre", "Landing")
DEFAULT_PAYLOADS: tuple[int, ...] = (0, 250, 500)


def compute_phase_payload_power(
    telemetry: pd.DataFrame,
    flights: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate mean power (W) per flight, main flight phase, and payload mass."""
    req_tel = {"flight", "phase", "power_w"}
    missing_tel = req_tel - set(telemetry.columns)
    if missing_tel:
        raise KeyError(f"telemetry is missing required columns: {sorted(missing_tel)}")

    req_fl = {"flight", "payload_g"}
    missing_fl = req_fl - set(flights.columns)
    if missing_fl:
        raise KeyError(f"flights is missing required columns: {sorted(missing_fl)}")

    fl_subset = flights[["flight", "payload_g"]].drop_duplicates(subset=["flight"]).copy()
    fl_subset["payload_g"] = fl_subset["payload_g"].astype(int)

    tel_filtered = telemetry.loc[
        telemetry["phase"].isin(MAIN_PHASES), ["flight", "phase", "power_w"]
    ]
    merged = tel_filtered.merge(fl_subset, on="flight", how="inner").dropna(
        subset=["phase", "payload_g", "power_w"]
    )
    if merged.empty:
        return pd.DataFrame(columns=["flight", "phase", "payload_g", "mean_power_w"])

    grouped = (
        merged.groupby(["flight", "phase", "payload_g"], as_index=False)["power_w"]
        .mean()
        .rename(columns={"power_w": "mean_power_w"})
    )
    return grouped


def summarize_payload_effect(phase_power: pd.DataFrame) -> dict[str, float]:
    """Compute mean +250 g step effect in watts and percentage across main phases."""
    if phase_power.empty:
        return {"delta_w": 0.0, "delta_pct": 0.0, "cruise_delta_w": 0.0, "cruise_delta_pct": 0.0}

    by_phase_pay = phase_power.groupby(["phase", "payload_g"])["mean_power_w"].mean().unstack()
    step_w_list: list[float] = []
    step_pct_list: list[float] = []

    for low_p, high_p in ((0, 250), (250, 500)):
        if low_p in by_phase_pay.columns and high_p in by_phase_pay.columns:
            valid = by_phase_pay[[low_p, high_p]].dropna()
            if not valid.empty:
                diff = valid[high_p] - valid[low_p]
                pct = (diff / valid[low_p]) * 100.0
                step_w_list.extend(diff.tolist())
                step_pct_list.extend(pct.tolist())

    cruise_delta_w = 0.0
    cruise_delta_pct = 0.0
    if "Cruise" in by_phase_pay.index and {0, 250}.issubset(by_phase_pay.columns):
        c0 = float(by_phase_pay.loc["Cruise", 0])
        c250 = float(by_phase_pay.loc["Cruise", 250])
        if pd.notna(c0) and pd.notna(c250) and c0 > 0:
            cruise_delta_w = c250 - c0
            cruise_delta_pct = (cruise_delta_w / c0) * 100.0

    delta_w = float(sum(step_w_list) / len(step_w_list)) if step_w_list else 0.0
    delta_pct = float(sum(step_pct_list) / len(step_pct_list)) if step_pct_list else 0.0
    return {
        "delta_w": delta_w,
        "delta_pct": delta_pct,
        "cruise_delta_w": cruise_delta_w,
        "cruise_delta_pct": cruise_delta_pct,
    }


def build_phase_payload_violin(
    phase_power: pd.DataFrame,
    show_points: bool = False,
    cut_y_axis: bool = True,
) -> go.Figure:
    """Build a 4-phase x 3-payload violin plot using monochromatic payload shades."""
    if phase_power.empty:
        fig = go.Figure()
        fig.update_layout(title="No flight phase power data available for current filters")
        return fig

    df = phase_power.copy()
    df["payload_g"] = df["payload_g"].astype(int)
    payloads = [p for p in DEFAULT_PAYLOADS if p in set(df["payload_g"])]
    if not payloads:
        payloads = sorted(df["payload_g"].unique().tolist())

    fig = go.Figure()
    payload_colors = PALETTES["payload"]

    for payload_g in payloads:
        sub = df[df["payload_g"] == payload_g]
        color = payload_colors.get(payload_g, "#3182bd")
        hover_text = [
            f"Flight {int(f)} · {ph} · {payload_g} g: {pw:.1f} W"
            for f, ph, pw in zip(sub["flight"], sub["phase"], sub["mean_power_w"], strict=True)
        ]
        fig.add_trace(
            go.Violin(
                x=sub["phase"],
                y=sub["mean_power_w"],
                name=f"{payload_g} g",
                legendgroup=f"{payload_g} g",
                scalegroup=f"{payload_g} g",
                box_visible=True,
                meanline_visible=True,
                points="all" if show_points else False,
                jitter=0.25 if show_points else 0.0,
                pointpos=0.0,
                marker={"size": 4, "opacity": 0.65, "color": color},
                line={"color": color, "width": 1.5},
                fillcolor=color,
                opacity=0.82,
                text=hover_text,
                hoverinfo="text",
            )
        )

    y_min_data = float(df["mean_power_w"].min())
    y_max_data = float(df["mean_power_w"].max())
    if cut_y_axis and y_min_data > 150.0:
        y_lower = max(0.0, round((y_min_data - 40.0) / 50.0) * 50.0)
    else:
        y_lower = 0.0
    y_upper = round((y_max_data + 50.0) / 50.0) * 50.0

    annotations: list[dict[str, object]] = []
    if y_lower > 0.0:
        annotations.append(
            {
                "text": f"Note: Y-axis starts at {int(y_lower)} W (cut axis).",
                "x": 0.0,
                "y": -0.18,
                "xref": "paper",
                "yref": "paper",
                "xanchor": "left",
                "yanchor": "top",
                "showarrow": False,
                "font": {"size": 11, "color": "#555555"},
            }
        )

    fig.update_layout(
        violinmode="group",
        violingap=0.2,
        violingroupgap=0.1,
        xaxis={
            "title": "Flight phase",
            "categoryorder": "array",
            "categoryarray": list(MAIN_PHASES),
        },
        yaxis={
            "title": "Mean power (W)",
            "range": [y_lower, y_upper],
        },
        legend={"title": {"text": "Payload (g)"}, "orientation": "h", "y": 1.08, "x": 0.0},
        annotations=annotations,
        margin={"l": 65, "r": 25, "t": 55, "b": 70 if y_lower > 0.0 else 45},
        height=470,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
