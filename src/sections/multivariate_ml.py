"""Multivariate Analysis & ML section (owner: UI & ML)."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st
from sklearn.ensemble import RandomForestRegressor

from src.theme import PALETTES


def render(tables: dict[str, pd.DataFrame]) -> None:
    """Render Multivariate correlations and baseline feature importance."""
    flights = tables["flights"]
    st.markdown("### Multivariate Analysis & ML")

    features = ["payload_g", "speed_mps", "altitude_m", "mean_airspeed_mps", "duration_s"]
    target = "cruise_power_w" if "cruise_power_w" in flights.columns else "mean_power_w"
    available = [c for c in features if c in flights.columns]

    col1, col2 = st.columns(2)

    with col1:
        corr = flights[available + [target]].corr()
        fig_corr = px.imshow(
            corr,
            text_auto=".2f",
            color_continuous_scale=PALETTES["diverging"],
            zmin=-1,
            zmax=1,
            title="Correlation across flight parameters and cruise power",
        )
        st.plotly_chart(fig_corr, key="ml_corr_heatmap")

    with col2:
        clean_df = flights[available + [target]].dropna()
        if len(clean_df) >= 10:
            X = clean_df[available]
            y = clean_df[target]
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X, y)

            imp_df = pd.DataFrame(
                {"Feature": available, "Importance": model.feature_importances_}
            ).sort_values("Importance", ascending=True)

            fig_imp = px.bar(
                imp_df,
                x="Importance",
                y="Feature",
                orientation="h",
                color="Importance",
                color_continuous_scale=PALETTES["viridis"],
                title=f"Random Forest feature importance (target: {target})",
            )
            st.plotly_chart(fig_imp, key="ml_rf_importance")
        else:
            st.warning("Not enough rows after filtering to fit the baseline model.")
