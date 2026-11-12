"""Visual theme, palettes, and Plotly template for Drone Delivery Energy Explorer."""

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

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
        "Takeoff": "#2a788e",
        "Climb": "#414487",
        "Cruise": "#22a884",
        "Descent": "#7ad151",
        "Landing": "#fde725",
        "Hover": "#440154",
    },
    "payload": {
        0: "#22a884",
        250: "#2a788e",
        500: "#414487",
        750: "#440154",
    },
    "categorical": [
        "#2a788e",
        "#22a884",
        "#414487",
        "#7ad151",
        "#440154",
        "#e66101",
    ],
    "diverging": [
        "#440154",
        "#3b528b",
        "#21918c",
        "#5ec962",
        "#fde725",
    ],
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


def apply_theme() -> None:
    """Register the shared Plotly template and apply clean spacing."""
    pio.templates["drone_explorer"] = plotly_template
    pio.templates.default = "drone_explorer"
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
