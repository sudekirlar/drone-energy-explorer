"""Visual theme, palettes, and Plotly template (pure Python, no Streamlit)."""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

from src.data import schema

# Colours follow the team-approved chart guide ("On grafik, tek soru"), so the dashboard
# matches the guide every chart was designed from.
PALETTES = {
    # Sequential, for quantities (power, energy, Wh/km).
    "viridis": [
        "#440154",
        "#414487",
        "#2a788e",
        "#22a884",
        "#7ad151",
        "#fde725",
    ],
    # Categorical, one colour per main phase; the same everywhere (map, cube, timeline, Sankey).
    "phase": {
        "Ground": "#9a968c",
        "Take-off": "#7a5195",
        "Cruise": "#2a78d6",
        "Manoeuvre": "#eda100",
        "Landing": "#1baf7a",
    },
    # Sub-phases use their main phase's colour; the second sub-phase of a pair is lighter.
    "sub_phase": {
        "Ground": "#9a968c",
        "Spool-up": "#b39bc8",
        "Climb": "#7a5195",
        "Straight leg": "#2a78d6",
        "Sloped cruise": "#8ab8ee",
        "WP turn": "#eda100",
        "Speed change": "#f5cd73",
        "Descent": "#1baf7a",
    },
    # Payload is ordinal: one hue, darker = heavier.
    "payload": {
        0: "#9ecae1",
        250: "#3182bd",
        500: "#08306b",
        750: "#041a3d",
    },
    # Categorical, for flights and K-means groups (no order implied).
    "categorical": [
        "#2a78d6",
        "#eb6834",
        "#1baf7a",
        "#eda100",
        "#6250d6",
        "#e87ba4",
        "#8a877f",
    ],
    # Diverging, for "observed minus predicted": blue below, grey at zero, red above.
    "diverging": [
        "#2166ac",
        "#67a9cf",
        "#d1e5f0",
        "#e0e0e0",
        "#fddbc7",
        "#ef8a62",
        "#b2182b",
    ],
}

assert set(PALETTES["phase"]) == set(schema.PHASES)
assert set(PALETTES["sub_phase"]) == set(schema.SUB_PHASES)


def get_plotly_template() -> go.layout.Template:
    """Return the shared Plotly template."""
    template = go.layout.Template()
    template.layout = go.Layout(
        font=dict(family="Inter, sans-serif", size=13),
        colorway=PALETTES["categorical"],
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=24, t=48, b=40),
        xaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)"),
        yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return template


plotly_template = get_plotly_template()


def register_plotly_template() -> None:
    """Register and activate the shared Plotly template."""
    pio.templates["drone_explorer"] = plotly_template
    pio.templates.default = "drone_explorer"
