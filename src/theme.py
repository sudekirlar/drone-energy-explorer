"""Visual theme, palettes, and Plotly template (pure Python, no Streamlit)."""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

from src.data import schema

# Colours follow the team-approved chart guide, so the dashboard
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
    # The lightness steps (L* about 37, 49, 61, 75 and 86 for Ground) keep the phases apart even
    # without colour vision; tests/test_colours.py checks this.
    "phase": {
        # Light grey: under deuteranomaly a mid grey looked almost like Landing's green.
        "Ground": "#d9d6cc",
        "Take-off": "#6e4689",
        "Cruise": "#2274d2",
        "Manoeuvre": "#f7a914",
        "Landing": "#06a873",
    },
    # Sub-phases use their main phase's colour; the second sub-phase of a pair is lighter.
    "sub_phase": {
        "Ground": "#d9d6cc",
        "Spool-up": "#b39bc8",
        "Climb": "#6e4689",
        "Straight leg": "#2274d2",
        "Sloped cruise": "#8ab8ee",
        "WP turn": "#f7a914",
        "Speed change": "#fcd479",
        "Descent": "#06a873",
    },
    # Payload is ordinal: one hue, darker = heavier.
    "payload": {
        0: "#9ecae1",
        250: "#3182bd",
        500: "#08306b",
        750: "#041a3d",
    },
    # Categorical, for flights and K-means groups (no order implied). Okabe & Ito (2008),
    # designed to stay distinguishable for the common types of colour-vision deficiency.
    "categorical": [
        "#0072B2",
        "#E69F00",
        "#CC79A7",
        "#009E73",
        "#56B4E9",
        "#D55E00",
        "#F0E442",
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

# Neutral colours for what is not data: text drawn on coloured cells, reference lines and the
# edges of points. Each one reads on both the light and the dark Streamlit theme.
NEUTRALS = {
    "text_dark": "#1d1c1a",  # text on a light cell
    "text_light": "#ffffff",  # text on a dark cell
    "reference": "rgba(128,128,128,0.7)",  # e.g. the "perfect prediction" line, error bars
    "outline": "rgba(255,255,255,0.7)",  # edge that keeps dark points visible on a dark page
}


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
