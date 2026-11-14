"""Unit tests for src/ml/regressor.py (Task C3).

The model is evaluated once, with one seed instead of five, and the result is shared by the
tests. Five seeds only make the published scores steadier; the behaviour these tests check
(shapes, thresholds, importance order, files written) is the same with one seed, and the suite
runs in seconds instead of more than a minute.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.ml import regressor
from src.ml.regressor import (
    REGRESSOR_FEATURES,
    RegressionArtifacts,
    build_and_save_artifacts,
    run_cruise_power_regression,
)


def _make_r1_flights(n: int = 54, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    payloads = np.tile([0, 250, 500], n // 3)
    speeds = np.repeat([4, 8, 12], n // 3)
    altitudes = np.tile([25.0, 50.0, 100.0], n // 3)

    cruise_power = (
        180.0
        + 0.14 * payloads
        + 1.8 * (speeds**2)
        + 0.15 * altitudes
        + rng.normal(0.0, 4.0, size=n)
    )

    df = pd.DataFrame(
        {
            "flight": np.arange(1, n + 1),
            "route": ["R1"] * n,
            "in_design": [True] * n,
            "payload_g": payloads,
            "speed_mps": speeds,
            "altitude_m": altitudes,
            "cruise_power_w": cruise_power,
        }
    )
    extra = pd.DataFrame(
        {
            "flight": [999],
            "route": ["R7"],
            "in_design": [False],
            "payload_g": [0],
            "speed_mps": [6],
            "altitude_m": [np.nan],
            "cruise_power_w": [250.0],
        }
    )
    return pd.concat([df, extra], ignore_index=True)


@pytest.fixture(scope="module")
def evaluated() -> RegressionArtifacts:
    """One evaluation of the synthetic flights, shared by the tests below."""
    return run_cruise_power_regression(_make_r1_flights(), seeds=(0,))


def test_run_cruise_power_regression_metrics_and_oof(evaluated: RegressionArtifacts) -> None:
    res = evaluated

    assert len(res.predictions) == 54
    assert res.metrics["n_flights"] == 54
    assert res.metrics["features"] == list(REGRESSOR_FEATURES)

    assert res.metrics["random_forest"]["cv"]["r2_mean"] > 0.85
    assert res.metrics["linear_regression"]["cv"]["r2_mean"] > 0.70
    assert res.metrics["random_forest"]["grouped_cv"]["r2"] > 0.70

    imp_features = [row["feature"] for row in res.metrics["permutation_importance"]]
    assert set(imp_features) == set(REGRESSOR_FEATURES)
    assert imp_features[0] == "speed_mps"


def test_build_and_save_artifacts_writes_parquet_and_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, evaluated: RegressionArtifacts
) -> None:
    # This test checks the files, not the model, so it reuses the shared evaluation.
    monkeypatch.setattr(
        regressor, "run_cruise_power_regression", lambda flights, **kwargs: evaluated
    )
    flights = _make_r1_flights()
    res = build_and_save_artifacts(flights=flights, output_dir=tmp_path)

    parquet_path = tmp_path / "ml_payload.parquet"
    json_path = tmp_path / "ml_metrics.json"
    assert parquet_path.exists()
    assert json_path.exists()

    loaded_df = pd.read_parquet(parquet_path)
    assert len(loaded_df) == len(res.predictions)


def test_regressor_validates_columns() -> None:
    flights = _make_r1_flights().drop(columns=["altitude_m"])
    with pytest.raises(KeyError):
        run_cruise_power_regression(flights)
