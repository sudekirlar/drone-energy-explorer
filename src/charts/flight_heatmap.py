"""Flight x time heatmap for telemetry phases and power (owner: uiml)."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.ml.clustering import run_kmeans
from src.theme import PALETTES

PHASE_ORDER: tuple[str, ...] = ("Ground", "Take-off", "Cruise", "Manoeuvre", "Landing")
PHASE_TO_CODE: dict[str, int] = {name: idx for idx, name in enumerate(PHASE_ORDER)}
SLICE_SECONDS: int = 2


def _discrete_phase_colorscale() -> list[list[float | str]]:
    """Build a step colorscale matching integer phase codes 0..N-1."""
    n = len(PHASE_ORDER)
    scale: list[list[float | str]] = []
    for idx, phase_name in enumerate(PHASE_ORDER):
        color = PALETTES["phase"][phase_name]
        low = idx / n
        high = (idx + 1) / n
        scale.append([low, color])
        scale.append([high, color])
    return scale


def _resolve_time_column(telemetry: pd.DataFrame) -> str:
    if "t_since_takeoff_s" in telemetry.columns:
        return "t_since_takeoff_s"
    if "t_s" in telemetry.columns:
        return "t_s"
    raise KeyError("telemetry must contain 't_since_takeoff_s' or 't_s'.")


def _assign_group_labels(
    flights_df: pd.DataFrame,
    order: str,
    k: int = 3,
    labels: pd.Series | Sequence[str] | None = None,
) -> pd.DataFrame:
    """Attach group keys, display labels, and sort keys to the flights table."""
    df = flights_df.copy().reset_index(drop=True)
    mode = order.strip().lower()

    if mode in {"altitude", "altitude_m"}:
        if "altitude_m" not in df.columns:
            raise KeyError("flights must contain 'altitude_m' when order='altitude'.")
        alt_int = df["altitude_m"].round().astype(int)
        df["_group_sort"] = alt_int
        df["_group_label"] = alt_int.map(lambda v: f"{v} m")
        df["_secondary_sort"] = df["speed_mps"] if "speed_mps" in df.columns else df["flight"]
    elif mode in {"speed", "speed_mps"}:
        if "speed_mps" not in df.columns:
            raise KeyError("flights must contain 'speed_mps' when order='speed'.")
        spd = df["speed_mps"].round(1)
        df["_group_sort"] = spd
        df["_group_label"] = spd.map(lambda v: f"{v:g} m/s")
        df["_secondary_sort"] = df["altitude_m"] if "altitude_m" in df.columns else df["flight"]
    elif mode in {"payload", "payload_g"}:
        if "payload_g" not in df.columns:
            raise KeyError("flights must contain 'payload_g' when order='payload'.")
        pay_int = df["payload_g"].round().astype(int)
        df["_group_sort"] = pay_int
        df["_group_label"] = pay_int.map(lambda v: f"{v} g")
        df["_secondary_sort"] = df["altitude_m"] if "altitude_m" in df.columns else df["flight"]
    elif mode in {"cluster", "kmeans", "k-means"}:
        if labels is not None:
            raw_series = pd.Series(labels, index=df.index).astype(str)
            grp_num = raw_series.str.extract(r"(\d+)", expand=False).fillna("99").astype(int)
            df["_group_sort"] = grp_num
            df["_group_label"] = grp_num.map(
                lambda g: f"Group {g}" if g < 99 else "Other routes (R2-R7)"
            )
        else:
            in_design_mask = (
                df["in_design"].astype(bool)
                if "in_design" in df.columns
                else pd.Series(True, index=df.index)
            )
            design_sub = df.loc[in_design_mask].reset_index(drop=True)
            df["_group_sort"] = 99
            df["_group_label"] = "Other routes (R2-R7)"
            if len(design_sub) >= k:
                res = run_kmeans(design_sub, k=k)
                grp_nums = res.labels.astype(str).str.extract(r"(\d+)", expand=False).astype(int)
                df.loc[in_design_mask, "_group_sort"] = grp_nums.to_numpy()
                df.loc[in_design_mask, "_group_label"] = [f"Group {g}" for g in grp_nums]
        df["_secondary_sort"] = df["altitude_m"] if "altitude_m" in df.columns else df["flight"]
    else:
        raise ValueError(
            f"Unsupported order={order!r}. Expected 'altitude', 'speed', 'payload', or 'cluster'."
        )

    df = df.sort_values(
        by=["_group_sort", "_secondary_sort", "flight"],
        ascending=[True, True, True],
    ).reset_index(drop=True)
    return df


def summarize_climb_band_by_altitude(
    telemetry: pd.DataFrame,
    flights: pd.DataFrame,
) -> dict[str, float]:
    """Measure how mean Take-off duration (s) expands from lowest to highest altitude."""
    if telemetry.empty or flights.empty:
        return {"min_alt": 0.0, "max_alt": 0.0, "min_climb_s": 0.0, "max_climb_s": 0.0}
    if not {"flight", "phase"}.issubset(telemetry.columns) or not {
        "flight",
        "altitude_m",
    }.issubset(flights.columns):
        return {"min_alt": 0.0, "max_alt": 0.0, "min_climb_s": 0.0, "max_climb_s": 0.0}

    design = flights[flights["in_design"]] if "in_design" in flights.columns else flights
    takeoff = telemetry[telemetry["phase"] == "Take-off"]
    counts = takeoff.groupby("flight").size().rename("climb_s").reset_index()
    merged = design[["flight", "altitude_m"]].merge(counts, on="flight", how="inner")
    if merged.empty:
        return {"min_alt": 0.0, "max_alt": 0.0, "min_climb_s": 0.0, "max_climb_s": 0.0}

    by_alt = merged.groupby("altitude_m")["climb_s"].mean().sort_index()
    return {
        "min_alt": float(by_alt.index[0]),
        "max_alt": float(by_alt.index[-1]),
        "min_climb_s": float(by_alt.iloc[0]),
        "max_climb_s": float(by_alt.iloc[-1]),
    }


def build_flight_time_heatmap(
    telemetry: pd.DataFrame,
    flights: pd.DataFrame,
    order: str = "altitude",
    color: str = "phase",
    include_other_routes: bool = False,
    k: int = 3,
    labels: pd.Series | Sequence[str] | None = None,
) -> go.Figure:
    """Build a flight x 2-second time slice heatmap coloured by phase or power."""
    if flights.empty or telemetry.empty:
        fig = go.Figure()
        fig.update_layout(title="No flights available for flight x time heatmap")
        return fig

    fl = flights.copy()
    if not include_other_routes and "in_design" in fl.columns:
        fl = fl.loc[fl["in_design"]].reset_index(drop=True)

    if fl.empty:
        fig = go.Figure()
        fig.update_layout(title="No flights match the active route and sidebar filters")
        return fig

    fl_sorted = _assign_group_labels(fl, order=order, k=k, labels=labels)
    ordered_flights = fl_sorted["flight"].tolist()

    time_col = _resolve_time_column(telemetry)
    color_mode = color.strip().lower()
    if color_mode not in {"phase", "power", "power_w"}:
        raise ValueError(f"Unsupported color={color!r}. Expected 'phase' or 'power'.")

    value_col = "phase" if color_mode == "phase" else "power_w"
    if value_col not in telemetry.columns:
        raise KeyError(f"telemetry must contain {value_col!r} when color={color!r}.")

    tel = telemetry.loc[
        telemetry["flight"].isin(ordered_flights), ["flight", time_col, value_col]
    ].dropna(subset=["flight", time_col, value_col])

    if tel.empty:
        fig = go.Figure()
        fig.update_layout(title="No telemetry samples available for selected flights")
        return fig

    tel = tel.copy()
    t_shifted = tel[time_col] - tel.groupby("flight")[time_col].transform("min")
    tel["_time_bin"] = (np.floor(t_shifted / SLICE_SECONDS) * SLICE_SECONDS).astype(int)

    time_bins = sorted(tel["_time_bin"].unique().tolist())
    bin_to_col = {b: idx for idx, b in enumerate(time_bins)}
    flight_to_row = {f: idx for idx, f in enumerate(ordered_flights)}

    n_rows = len(ordered_flights)
    n_cols = len(time_bins)
    z = np.full((n_rows, n_cols), np.nan, dtype=float)
    hover = np.full((n_rows, n_cols), "", dtype=object)

    meta_lookup = fl_sorted.set_index("flight")["_group_label"].to_dict()

    if color_mode == "phase":
        tel["_code"] = tel["phase"].map(PHASE_TO_CODE).fillna(-1).astype(int)
        valid_tel = tel[tel["_code"] >= 0]
        agg = (
            valid_tel.groupby(["flight", "_time_bin"])["_code"]
            .agg(lambda s: int(s.mode().iloc[0]))
            .reset_index()
        )
        for row in agg.itertuples(index=False):
            r_idx = flight_to_row[row.flight]
            c_idx = bin_to_col[row._time_bin]
            code = int(row._code)
            phase_name = PHASE_ORDER[code]
            z[r_idx, c_idx] = float(code)
            grp_lbl = meta_lookup.get(row.flight, "")
            hover[r_idx, c_idx] = (
                f"Flight {int(row.flight)} ({grp_lbl}) · t = {row._time_bin} s: {phase_name}"
            )
    else:
        agg = tel.groupby(["flight", "_time_bin"])["power_w"].mean().reset_index()
        for row in agg.itertuples(index=False):
            r_idx = flight_to_row[row.flight]
            c_idx = bin_to_col[row._time_bin]
            pw = float(row.power_w)
            z[r_idx, c_idx] = pw
            grp_lbl = meta_lookup.get(row.flight, "")
            hover[r_idx, c_idx] = (
                f"Flight {int(row.flight)} ({grp_lbl}) · t = {row._time_bin} s: {pw:.0f} W"
            )

    y_labels = [f"F{int(f)}" for f in ordered_flights]

    if color_mode == "phase":
        heatmap_trace = go.Heatmap(
            z=z,
            x=time_bins,
            y=y_labels,
            text=hover,
            hoverinfo="text",
            colorscale=_discrete_phase_colorscale(),
            zmin=-0.5,
            zmax=len(PHASE_ORDER) - 0.5,
            colorbar={
                "title": "Phase",
                "tickmode": "array",
                "tickvals": list(range(len(PHASE_ORDER))),
                "ticktext": list(PHASE_ORDER),
                "len": 0.65,
            },
        )
    else:
        heatmap_trace = go.Heatmap(
            z=z,
            x=time_bins,
            y=y_labels,
            text=hover,
            hoverinfo="text",
            colorscale=PALETTES["viridis"],
            colorbar={
                "title": "Power (W)",
                "len": 0.65,
            },
        )

    fig = go.Figure(data=[heatmap_trace])

    shapes: list[dict[str, object]] = []
    annotations: list[dict[str, object]] = []
    group_labels = fl_sorted["_group_label"].tolist()

    start_idx = 0
    while start_idx < n_rows:
        curr_label = group_labels[start_idx]
        end_idx = start_idx
        while end_idx + 1 < n_rows and group_labels[end_idx + 1] == curr_label:
            end_idx += 1

        mid_idx = 0.5 * (start_idx + end_idx)
        annotations.append(
            {
                "text": f"{curr_label} ({end_idx - start_idx + 1})",
                "x": 1.01,
                "y": mid_idx,
                "xref": "paper",
                "yref": "y",
                "xanchor": "left",
                "yanchor": "middle",
                "showarrow": False,
                "font": {"size": 11, "color": "#222222"},
            }
        )

        if start_idx > 0:
            shapes.append(
                {
                    "type": "line",
                    "x0": 0.0,
                    "x1": 1.0,
                    "y0": start_idx - 0.5,
                    "y1": start_idx - 0.5,
                    "xref": "paper",
                    "yref": "y",
                    "line": {"color": "#111111", "width": 1.6},
                }
            )
        start_idx = end_idx + 1

    tick_step = max(1, n_rows // 12)
    tick_indices = list(range(0, n_rows, tick_step))

    fig.update_layout(
        xaxis={
            "title": "Time since take-off (s, 2 s slices)",
            "showgrid": False,
        },
        yaxis={
            "title": f"Flights sorted by {order} (n = {n_rows})",
            "tickmode": "array",
            "tickvals": [y_labels[i] for i in tick_indices],
            "ticktext": [y_labels[i] for i in tick_indices],
            "autorange": "reversed",
            "showgrid": False,
        },
        shapes=shapes,
        annotations=annotations,
        margin={"l": 70, "r": 145, "t": 35, "b": 50},
        height=620,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
