"""K-means clustering of flights on standardized energy and flight outcomes (Task C2)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

CLUSTER_FEATURES: tuple[str, ...] = (
    "energy_wh",
    "wh_per_km",
    "duration_s",
    "cruise_power_w",
    "climb_power_w",
)


@dataclass(frozen=True)
class KMeansResult:
    """Container for K-means cluster assignments and quality metrics."""

    labels: pd.Series
    silhouette: float
    cluster_summary: pd.DataFrame


def run_kmeans(
    flights: pd.DataFrame,
    k: int = 3,
    random_state: int = 42,
    n_init: int = 20,
) -> KMeansResult:
    """Cluster flights into k groups ordered from lowest to highest mean energy (G1..Gk).

    Uses the five standardized outcome measures defined in Task C2:
    energy_wh, wh_per_km, duration_s, cruise_power_w, climb_power_w.
    """
    if k < 2:
        raise ValueError(f"k must be at least 2, got {k}")

    missing = [col for col in CLUSTER_FEATURES if col not in flights.columns]
    if missing:
        raise KeyError(f"Missing required clustering columns: {missing}")

    valid_mask = flights[list(CLUSTER_FEATURES)].notna().all(axis=1)
    clean_df = flights.loc[valid_mask].copy()

    if len(clean_df) <= k:
        raise ValueError(f"Not enough complete flights ({len(clean_df)}) to form k={k} clusters.")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(clean_df[list(CLUSTER_FEATURES)].to_numpy(dtype=float))

    model = KMeans(n_clusters=k, n_init=n_init, random_state=random_state)
    raw_clusters = model.fit_predict(X_scaled)

    # Order clusters by mean total energy ascending so G1 is always the lowest-energy group
    clean_df["_raw_cluster"] = raw_clusters
    mean_energy_by_cluster = (
        clean_df.groupby("_raw_cluster")["energy_wh"].mean().sort_values(ascending=True)
    )
    rank_map = {
        raw_id: f"G{rank}"
        for rank, raw_id in enumerate(mean_energy_by_cluster.index.tolist(), start=1)
    }

    ordered_labels = clean_df["_raw_cluster"].map(rank_map)
    full_labels = pd.Series(pd.NA, index=flights.index, dtype="string", name="cluster")
    full_labels.loc[clean_df.index] = ordered_labels.astype("string")

    if len(set(raw_clusters)) > 1:
        sil = float(silhouette_score(X_scaled, raw_clusters))
    else:
        sil = float("nan")

    clean_df["cluster"] = ordered_labels
    summary = (
        clean_df.groupby("cluster", as_index=False)
        .agg(
            n_flights=("energy_wh", "count"),
            mean_energy_wh=("energy_wh", "mean"),
            mean_wh_per_km=("wh_per_km", "mean"),
            mean_duration_s=("duration_s", "mean"),
            mean_cruise_power_w=("cruise_power_w", "mean"),
            mean_climb_power_w=("climb_power_w", "mean"),
        )
        .sort_values("cluster")
        .reset_index(drop=True)
    )

    return KMeansResult(
        labels=full_labels,
        silhouette=sil,
        cluster_summary=summary,
    )
