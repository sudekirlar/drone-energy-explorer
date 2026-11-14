"""G6 · Payload x speed heatmap of cruise power, with the Random Forest views (owner: Platform).

Rows are the three payloads, columns the five target speeds; every cell holds the R1 design
flights flown with that payload and speed (9-14 flights each). A view chooses what a cell shows:

    observed  mean measured cruise power (W)
    rf        mean Random Forest prediction (W)
    rf_gap    observed minus Random Forest (W)
    lin_gap   observed minus linear regression (W)

The predictions come from ``ml_payload`` (src/ml/regressor.py): every flight's prediction was
made by a model that never saw that flight. Two smaller figures show the model per flight
(prediction against measurement) and which feature it relies on (permutation importance from
``ml_metrics.json``).

No Streamlit here (tests/test_architecture.py).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src import theme

VIEWS = ("observed", "rf", "rf_gap", "lin_gap")
GAP_VIEWS = ("rf_gap", "lin_gap")
FEATURE_LABEL = {"payload_g": "Payload", "speed_mps": "Speed", "altitude_m": "Altitude"}
# A neutral reference line (the "perfect prediction" diagonal), not a data colour.
REFERENCE_LINE = "rgba(128,128,128,0.7)"


def _signed(x: float) -> str:
    """'+8.0 W' or '−4.5 W', with a real minus sign; a value that rounds to zero is '0.0 W'."""
    x = round(x, 1)
    if x == 0:
        return "0.0 W"
    return f"{'+' if x > 0 else '−'}{abs(x):.1f} W"


# Cell text is dark on light cells and white on dark cells. Streamlit's chart theme gives all
# chart text one colour, which was unreadable on yellow cells in dark mode.
DARK_TEXT, LIGHT_TEXT = "#1d1c1a", "#ffffff"


def _text_colour(hex_colour: str) -> str:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return DARK_TEXT if luminance > 0.45 else LIGHT_TEXT


def _colour_at(scale: list[str], t: float) -> str:
    """The palette colour nearest to position t (0-1) on an evenly spaced colour scale."""
    t = min(1.0, max(0.0, t))
    return scale[round(t * (len(scale) - 1))]


# ---- data shaping --------------------------------------------------------------------------


def model_data(flights: pd.DataFrame, ml_payload: pd.DataFrame) -> pd.DataFrame:
    """One row per R1 design flight on screen: settings, measurement and both predictions."""
    design = flights.loc[flights["in_design"].astype(bool), ["flight", "payload_g", "speed_mps"]]
    data = design.merge(ml_payload, on="flight", how="inner")
    data["rf_gap"] = data["cruise_power_w"] - data["rf_pred_w"]
    data["lin_gap"] = data["cruise_power_w"] - data["linear_pred_w"]
    return data


def cell_table(data: pd.DataFrame) -> pd.DataFrame:
    """One row per (payload, speed) cell: number of flights and the mean of every view."""
    cells = (
        data.groupby(["payload_g", "speed_mps"])
        .agg(
            flights=("flight", "size"),
            observed=("cruise_power_w", "mean"),
            rf=("rf_pred_w", "mean"),
            linear=("linear_pred_w", "mean"),
        )
        .reset_index()
    )
    cells["rf_gap"] = cells["observed"] - cells["rf"]
    cells["lin_gap"] = cells["observed"] - cells["linear"]
    return cells


def _pivot(cells: pd.DataFrame, column: str) -> pd.DataFrame:
    return cells.pivot(index="payload_g", columns="speed_mps", values=column).sort_index()


# ---- figures -------------------------------------------------------------------------------


def _empty(text: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=text, showarrow=False)
    fig.update_layout(xaxis_visible=False, yaxis_visible=False, height=200)
    return fig


def _hover(row: pd.Series) -> str:
    n = int(row["flights"])
    return (
        f"<b>{int(row['payload_g'])} g · {int(row['speed_mps'])} m/s</b> · "
        f"{n} flight{'s' if n != 1 else ''}<br>"
        f"measured {row['observed']:.0f} W<br>"
        f"Random Forest {row['rf']:.0f} W (difference {_signed(row['rf_gap'])})<br>"
        f"linear model {row['linear']:.0f} W (difference {_signed(row['lin_gap'])})"
    )


def build_payload_heatmap(
    flights: pd.DataFrame, ml_payload: pd.DataFrame, view: str = "observed"
) -> go.Figure:
    """Payload x speed grid; the colour scale is shared by the two power views and by the two
    difference views, so switching views compares like with like."""
    data = model_data(flights, ml_payload)
    if data.empty:
        return _empty("No R1 flights with model predictions match the filters.")
    cells = cell_table(data)
    cells["hover"] = cells.apply(_hover, axis=1)
    cells["label"] = [
        (
            _signed(r[view])
            if view in GAP_VIEWS
            else f"{r[view]:.0f} W<br>{int(r['flights'])} flights"
        )
        for _, r in cells.iterrows()
    ]

    z = _pivot(cells, view)
    if view in GAP_VIEWS:
        reach = max(5.0, float(cells[list(GAP_VIEWS)].abs().max().max()))
        scale = dict(
            colorscale=theme.PALETTES["diverging"],
            zmin=-reach,
            zmax=reach,
            colorbar=dict(title=dict(text="measured −<br>predicted (W)"), thickness=12),
        )
    else:
        both = cells[["observed", "rf"]]
        scale = dict(
            colorscale=theme.PALETTES["viridis"],
            zmin=float(both.min().min()),
            zmax=float(both.max().max()),
            colorbar=dict(title=dict(text="cruise<br>power (W)"), thickness=12),
        )

    fig = go.Figure(
        go.Heatmap(
            z=z.values,
            x=[f"{s} m/s" for s in z.columns],
            y=[f"{p} g" for p in z.index],
            customdata=_pivot(cells, "hover").values,
            hovertemplate="%{customdata}<extra></extra>",
            xgap=3,
            ygap=3,
            **scale,
        )
    )
    # Cell labels are annotations, so each can have its own text colour (see _text_colour).
    span = scale["zmax"] - scale["zmin"] or 1.0
    for _, r in cells.iterrows():
        t = (r[view] - scale["zmin"]) / span
        fig.add_annotation(
            x=f"{int(r['speed_mps'])} m/s",
            y=f"{int(r['payload_g'])} g",
            text=r["label"],
            showarrow=False,
            font=dict(size=12, color=_text_colour(_colour_at(scale["colorscale"], t))),
        )
    fig.update_layout(
        height=330,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(title="Target speed", showgrid=False),
        yaxis=dict(title="Payload", showgrid=False),
    )
    return fig


def build_prediction_scatter(
    flights: pd.DataFrame, ml_payload: pd.DataFrame, model: str = "rf"
) -> go.Figure:
    """Each flight: the model's prediction against the measurement, coloured by payload."""
    data = model_data(flights, ml_payload)
    if data.empty:
        return _empty("No flights to show.")
    column, name = ("rf_pred_w", "Random Forest") if model == "rf" else ("linear_pred_w", "Linear")
    fig = go.Figure()
    for payload, rows in data.groupby("payload_g"):
        fig.add_trace(
            go.Scatter(
                x=rows[column],
                y=rows["cruise_power_w"],
                mode="markers",
                name=f"{int(payload)} g",
                # The thin light edge keeps the darkest payload colour visible on a dark page.
                marker=dict(
                    size=7,
                    color=theme.PALETTES["payload"].get(int(payload)),
                    line=dict(width=0.6, color="rgba(255,255,255,0.7)"),
                ),
                customdata=rows[["flight", "speed_mps"]],
                hovertemplate=(
                    "flight %{customdata[0]} · %{customdata[1]} m/s<br>predicted %{x:.0f} W"
                    "<br>measured %{y:.0f} W<extra>%{fullData.name}</extra>"
                ),
            )
        )
    lo = float(min(data[column].min(), data["cruise_power_w"].min())) - 5
    hi = float(max(data[column].max(), data["cruise_power_w"].max())) + 5
    fig.add_trace(
        go.Scatter(
            x=[lo, hi],
            y=[lo, hi],
            mode="lines",
            line=dict(color=REFERENCE_LINE, dash="dash", width=1),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.update_layout(
        title=dict(text=f"Each flight: {name} prediction and measurement", font=dict(size=13)),
        height=380,
        xaxis=dict(title="predicted cruise power (W)", range=[lo, hi]),
        yaxis=dict(title="measured cruise power (W)", range=[lo, hi]),
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(
            title=dict(text="Payload"), orientation="h", x=0, xanchor="left", y=-0.25, yanchor="top"
        ),
    )
    return fig


def build_importance(metrics: dict) -> go.Figure:
    """How much the Random Forest's R² falls when one feature is shuffled (mean ± std)."""
    rows = metrics.get("permutation_importance") or []
    if not rows:
        return _empty("Feature importance is not available yet.")
    rows = sorted(rows, key=lambda r: r["importance_mean"])
    fig = go.Figure(
        go.Bar(
            x=[r["importance_mean"] for r in rows],
            y=[FEATURE_LABEL.get(r["feature"], r["feature"]) for r in rows],
            orientation="h",
            error_x=dict(
                type="data", array=[r["importance_std"] for r in rows], color=REFERENCE_LINE
            ),
            marker_color=theme.PALETTES["categorical"][0],
            hovertemplate="shuffling %{y} lowers R² by %{x:.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(text="Drop in R² when a feature is shuffled", font=dict(size=13)),
        height=380,
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(title="drop in R²", rangemode="tozero"),
    )
    return fig


# ---- scores and finding --------------------------------------------------------------------


def _r2(cv: dict) -> str:
    """'0.79 ± 0.01'; a spread that rounds to zero is written '± <0.01', not '± 0.00'."""
    std = cv["r2_std"]
    return f"{cv['r2_mean']:.2f} ± " + (f"{std:.2f}" if std >= 0.005 else "<0.01")


def model_scores(metrics: dict) -> dict[str, str] | None:
    """The three headline numbers of ml_metrics.json, formatted for the card."""
    try:
        rf, lin = metrics["random_forest"], metrics["linear_regression"]
        return {
            "rf": _r2(rf["cv"]),
            "rf_mae": f"{rf['cv']['mae_mean']:.1f} W",
            "lin": _r2(lin["cv"]),
            "lin_mae": f"{lin['cv']['mae_mean']:.1f} W",
            "unseen": f"{rf['grouped_cv']['r2']:.2f} / {lin['grouped_cv']['r2']:.2f}",
        }
    except (KeyError, TypeError):
        return None


def _cell_name(row: pd.Series) -> str:
    return f"{int(row['payload_g'])} g and {int(row['speed_mps'])} m/s"


def describe_payload_heatmap(
    flights: pd.DataFrame, ml_payload: pd.DataFrame, view: str = "observed"
) -> str | None:
    """One or two sentences about the cells on screen, for the chosen view."""
    data = model_data(flights, ml_payload)
    if data.empty:
        return None
    cells = cell_table(data)

    if view == "observed":
        parts = []
        by_payload = data.groupby("payload_g")["cruise_power_w"].mean()
        if len(by_payload) > 1:
            lo_p, hi_p = by_payload.index[0], by_payload.index[-1]
            step = (by_payload[hi_p] - by_payload[lo_p]) / ((hi_p - lo_p) / 250)
            parts.append(
                f"Cruise power goes from {by_payload[lo_p]:.0f} W at {lo_p} g to "
                f"{by_payload[hi_p]:.0f} W at {hi_p} g, about {step:.0f} W for every 250 g."
            )
        by_speed = data.groupby("speed_mps")["cruise_power_w"].mean()
        if len(by_speed) > 1:
            parts.append(
                f"Across speeds it is lowest at {by_speed.idxmin()} m/s ({by_speed.min():.0f} W) "
                f"and highest at {by_speed.idxmax()} m/s ({by_speed.max():.0f} W)."
            )
        if not parts:
            row = cells.iloc[0]
            parts.append(f"The flights at {_cell_name(row)} cruise at {row['observed']:.0f} W.")
        return " ".join(parts)

    if view == "rf":
        lo, hi = cells.loc[cells["rf"].idxmin()], cells.loc[cells["rf"].idxmax()]
        return (
            f"The Random Forest predicts the least power at {_cell_name(lo)} ({lo['rf']:.0f} W) "
            f"and the most at {_cell_name(hi)} ({hi['rf']:.0f} W). The measured values on screen "
            f"go from {cells['observed'].min():.0f} W to {cells['observed'].max():.0f} W."
        )

    model = "Random Forest" if view == "rf_gap" else "linear model"
    gap = cells[view]
    under, over = cells.loc[gap.idxmax()], cells.loc[gap.idxmin()]
    pieces = []
    if under[view] > 0:
        pieces.append(
            f"{_signed(under[view])} at {_cell_name(under)}, where it predicts too little"
        )
    if over[view] < 0:
        pieces.append(f"{_signed(over[view])} at {_cell_name(over)}, where it predicts too much")
    first = f"The {model}'s largest gaps are " + ", and ".join(pieces) + "." if pieces else ""
    return (
        f"{first} On average, a cell is {gap.abs().mean():.1f} W away from the measurement."
    ).strip()
