"""The pipeline's model step: it hands the new flights table to the regression and writes both
of its output files. The model itself is tested in tests/test_regressor.py."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.data import pipeline
from src.ml import regressor


def test_model_step_writes_both_files_from_the_given_flights(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    flights = pd.DataFrame({"flight": [1, 2, 3], "cruise_power_w": [450.0, 500.0, 550.0]})
    seen: list[pd.DataFrame] = []

    def instant(given: pd.DataFrame, **kwargs) -> regressor.RegressionArtifacts:
        seen.append(given)
        predictions = given[["flight", "cruise_power_w"]].assign(
            rf_pred_w=given["cruise_power_w"] + 1, linear_pred_w=given["cruise_power_w"] - 1
        )
        cv = {"r2_mean": 0.8, "r2_std": 0.01, "mae_mean": 15.0, "mae_std": 0.3}
        metrics = {
            "n_flights": len(given),
            "random_forest": {"cv": cv},
            "linear_regression": {"cv": cv},
        }
        return regressor.RegressionArtifacts(predictions=predictions, metrics=metrics)

    monkeypatch.setattr(regressor, "run_cruise_power_regression", instant)

    metrics = pipeline.write_model(flights, tmp_path)

    assert seen and seen[0] is flights
    assert len(pd.read_parquet(tmp_path / "ml_payload.parquet")) == 3
    assert json.loads((tmp_path / "ml_metrics.json").read_text())["n_flights"] == 3
    assert metrics["n_flights"] == 3
