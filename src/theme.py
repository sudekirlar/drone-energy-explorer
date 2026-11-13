"""Visual theme, palettes, and Plotly template (pure Python, no Streamlit)."""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

from src.data import schema

PALETTES = {
    "viridis": [
        "#440154",
        "#414487",
        "#2a788e",
        "#22a884",
        "#7ad151",
        "#fde725",
    ],
    "phase": {
        "Ground": "#8c969e",
        "Take-off": "#2a788e",
        "Cruise": "#22a884",
        "Manoeuvre": "#414487",
        "Landing": "#d95f02",
    },
    "sub_phase": {
        "Ground": "#8c969e",
        "Spool-up": "#56b4e9",
        "Climb": "#2a788e",
        "Straight leg": "#22a884",
        "Sloped cruise": "#66c2a5",
        "WP turn": "#414487",
        "Speed change": "#7570b3",
        "Descent": "#d95f02",
    },
    "payload": {
        0: "#bdd7e7",
        250: "#6baed6",
        500: "#3182bd",
        750: "#08519c",
    },
    "categorical": [
        "#2a788e",
        "#22a884",
        "#414487",
        "#e66101",
        "#7570b3",
        "#66a61e",
        "#a6761d",
    ],
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
