"""Unit tests for src/ml/clustering.py (Task C2)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.loader import load_table
from src.ml.clustering import CLUSTER_FEATURES, run_kmeans


def _make_sample_flights(n: int = 45, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    regime = np.repeat([0, 1, 2], n // 3)
    payloads = np.where(regime == 0, 0, np.where(regime == 1, 250, 500))
    base_energy = 40.0 + regime * 35.0 + rng.normal(0, 3.0, size=n)

    return pd.DataFrame(
        {
            "flight": np.arange(1, n + 1),
            "payload_g": payloads,
            "energy_wh": base_energy,
            "wh_per_km": 22.0 + regime * 12.0 + rng.normal(0, 1.5, size=n),
            "duration_s": 210.0 + regime * 60.0 + rng.normal(0, 8.0, size=n),
            "cruise_power_w": 240.0 + regime * 75.0 + rng.normal(0, 10.0, size=n),
            "climb_power_w": 320.0 + regime * 85.0 + rng.normal(0, 12.0, size=n),
        }
    )


def test_run_kmeans_orders_labels_by_energy() -> None:
    flights = _make_sample_flights()
    res = run_kmeans(flights, k=3)

    assert set(res.labels.dropna().unique()) == {"G1", "G2", "G3"}
    assert -1.0 <= res.silhouette <= 1.0

    means = res.cluster_summary.set_index("cluster")["mean_energy_wh"]
    assert means["G1"] < means["G2"] < means["G3"]
    g1_payloads = flights.loc[res.labels == "G1", "payload_g"]
    assert (g1_payloads == 500).sum() == 0


def test_run_kmeans_on_project_sample_flights() -> None:
    all_all_flights = load_table("flights")
    flights = all_flights.loc[all_flights["in_design"]].reset_index(drop=True)
    flights = all_flights.loc[all_flights["in_design"]].reset_index(drop=True)
    res = run_kmeans(flights, k=3)

    assert set(res.labels.dropna().unique()) == {"G1", "G2", "G3"}
    assert 0.15 <= res.silhouette <= 0.65
    g1_payloads = flights.loc[res.labels == "G1", "payload_g"]
    assert (g1_payloads == 500).sum() == 0


def test_run_kmeans_is_deterministic_and_handles_missing() -> None:
    flights = _make_sample_flights()
    flights.loc[0, "climb_power_w"] = np.nan

    res1 = run_kmeans(flights, k=3)
    res2 = run_kmeans(flights, k=3)

    assert pd.isna(res1.labels.iloc[0])
    assert res1.labels.dropna().equals(res2.labels.dropna())
    assert res1.silhouette == pytest.approx(res2.silhouette)


def test_run_kmeans_validates_inputs() -> None:
    flights = _make_sample_flights()
    with pytest.raises(ValueError):
        run_kmeans(flights, k=1)

    with pytest.raises(KeyError):
        run_kmeans(flights.drop(columns=[CLUSTER_FEATURES[0]]), k=3)
