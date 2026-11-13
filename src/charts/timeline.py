"""Four-panel flight telemetry timeline and estimated phase bands (G3)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.theme import PALETTES


def build_timeline(
    telemetry: pd.DataFrame,
    flight_id: int,
    show_phases: bool = True,
) -> go.Figure:
    """Plot power, two speeds, altitude and voltage for one flight."""
    data = telemetry.loc[telemetry["flight"] == flight_id].sort_values("t_s")
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.06)
    if data.empty:
        return fig.update_layout(title="No telemetry for selected flight")
    x = data["t_s"]
    traces = [
        (1, "power_w", "Power (W)", "#2a788e"),
        (2, "ground_speed_mps", "Ground speed (m/s)", "#22a884"),
        (2, "airspeed_mps", "Airspeed (anemometer, m/s)", "#414487"),
        (3, "alt_rel_m", "Relative altitude (m)", "#e66101"),
        (4, "voltage_v", "Voltage (V)", "#7570b3"),
    ]
    for row, col, name, color in traces:
        fig.add_trace(
            go.Scatter(x=x, y=data[col], mode="lines", name=name, line={"color": color}),
            row=row,
            col=1,
        )
    for row, title in enumerate(["Power (W)", "Speed (m/s)", "Altitude (m)", "Voltage (V)"], 1):
        fig.update_yaxes(title_text=title, row=row, col=1)
    fig.update_xaxes(title_text="Time from recording start (s)", row=4, col=1)

    # Phase labels are computed by Platform. Never infer or invent them here.
    if show_phases and "phase" in data and data["phase"].notna().any():
        phases = data["phase"].fillna("Unlabelled").tolist()
        starts = [0] + [i for i in range(1, len(phases)) if phases[i] != phases[i - 1]]
        for si, start in enumerate(starts):
            end = starts[si + 1] if si + 1 < len(starts) else len(data) - 1
            phase = phases[start]
            if phase not in PALETTES["phase"]:
                continue
            left = float(data["t_s"].iloc[start])
            right = float(data["t_s"].iloc[end])
            if right <= left:
                continue
            fig.add_vrect(
                x0=left,
                x1=right,
                fillcolor=PALETTES["phase"][phase],
                opacity=0.11,
                line_width=0,
                layer="below",
            )
        if "sub_phase" in data:
            turns = data.loc[data["sub_phase"] == "WP turn", "t_s"]
            if not turns.empty:
                # Annotate the midpoint of each contiguous turn interval, not every raw sample.
                turn_mask = data["sub_phase"].eq("WP turn")
                groups = turn_mask.ne(turn_mask.shift()).cumsum()
                for _, group in data.loc[turn_mask].groupby(groups[turn_mask]):
                    fig.add_vline(
                        x=float(group["t_s"].median()),
                        line={
                            "color": PALETTES["sub_phase"]["WP turn"],
                            "width": 1.5,
                            "dash": "dot",
                        },
                    )
    fig.update_layout(
        title=f"Flight {flight_id} • power, speed, altitude and voltage",
        height=800,
        hovermode="x unified",
        legend={"orientation": "h"},
        margin={"t": 72, "b": 32},
    )
    return fig
