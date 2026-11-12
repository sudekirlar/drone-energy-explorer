"""Multivariate & ML section for Drone Delivery Energy Explorer."""

import pandas as pd
import plotly.express as px
from sklearn.ensemble import RandomForestRegressor
import streamlit as st

from src.data.filters import FilterState
from src.theme import PALETTES


def render(df: pd.DataFrame, filters: FilterState) -> None:
    """Render Multivariate correlations and feature importance."""
    st.markdown("### Multivariate Analysis & Feature Importance")

    feature_candidates = [
        "payload_g",
        "target_altitude",
        "target_speed",
        "wind_speed",
        "duration_s",
    ]
    available_features = [c for c in feature_candidates if c in df.columns]

    if len(available_features) < 2 or "total_energy_wh" not in df.columns:
        st.info("Insufficient numeric columns for multivariate modeling.")
        return

    col1, col2 = st.columns(2)

    with col1:
        corr = df[available_features + ["total_energy_wh"]].corr()
        fig_corr = px.imshow(
            corr,
            text_auto=".2f",
            color_continuous_scale=PALETTES["diverging"],
            zmin=-1,
            zmax=1,
            title="Feature Correlation Matrix",
        )
        st.plotly_chart(fig_corr, use_container_width=True)

    with col2:
        clean_df = df[available_features + ["total_energy_wh"]].dropna()
        if len(clean_df) >= 10:
            X = clean_df[available_features]
            y = clean_df["total_energy_wh"]
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X, y)

            imp_df = pd.DataFrame(
                {
                    "Feature": available_features,
                    "Importance": model.feature_importances_,
                }
            ).sort_values("Importance", ascending=True)

            fig_imp = px.bar(
                imp_df,
                x="Importance",
                y="Feature",
                orientation="h",
                color="Importance",
                color_continuous_scale=PALETTES["viridis"],
                title="Random Forest Feature Importance (Target: Total Energy)",
            )
            st.plotly_chart(fig_imp, use_container_width=True)
        else:
            st.warning("Not enough rows after filtering to fit the model.")
