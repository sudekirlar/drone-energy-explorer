"""Cruise power regression module (Task C3 · owner: uiml)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold, KFold

from src.data import loader, schema

REGRESSOR_FEATURES: tuple[str, ...] = ("payload_g", "speed_mps", "altitude_m")
TARGET_COL: str = "cruise_power_w"
DEFAULT_SEEDS: tuple[int, ...] = (0, 1, 2, 3, 4)
N_SPLITS: int = 5


@dataclass(frozen=True)
class RegressionArtifacts:
    """Container for Task C3 out-of-fold predictions and evaluation metrics."""

    predictions: pd.DataFrame
    metrics: dict[str, Any]


def _prepare_r1_dataset(flights: pd.DataFrame) -> pd.DataFrame:
    """Filter R1 design flights with finite target and feature values."""
    required = {"flight", TARGET_COL, *REGRESSOR_FEATURES}
    missing = required - set(flights.columns)
    if missing:
        raise KeyError(f"flights table is missing required columns: {sorted(missing)}")

    df = flights.copy()
    if "in_design" in df.columns:
        df = df[df["in_design"].astype(bool)].copy()
    elif "route" in df.columns:
        df = df[df["route"] == "R1"].copy()

    cols = list(REGRESSOR_FEATURES) + [TARGET_COL]
    df = df.dropna(subset=cols).reset_index(drop=True)
    if len(df) < N_SPLITS:
        raise ValueError(f"At least {N_SPLITS} valid R1 flights are required, got {len(df)}.")
    return df


def _make_rf(seed: int) -> RandomForestRegressor:
    return RandomForestRegressor(
        n_estimators=200,
        random_state=seed,
        n_jobs=-1,
    )


def _evaluate_repeated_kfold(
    X: np.ndarray,
    y: np.ndarray,
    seeds: tuple[int, ...],
    n_splits: int,
) -> tuple[dict[str, float], dict[str, float], np.ndarray, np.ndarray]:
    """Run n_splits K-Fold CV across multiple seeds for RF and Linear Regression."""
    rf_r2, rf_mae = [], []
    lr_r2, lr_mae = [], []

    rf_oof_accum = np.zeros((len(seeds), len(y)), dtype=float)
    lr_oof_accum = np.zeros((len(seeds), len(y)), dtype=float)

    for s_idx, seed in enumerate(seeds):
        kf = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
        rf_oof = np.empty(len(y), dtype=float)
        lr_oof = np.empty(len(y), dtype=float)

        for train_idx, test_idx in kf.split(X):
            X_tr, y_tr = X[train_idx], y[train_idx]
            X_te = X[test_idx]

            rf = _make_rf(seed)
            rf.fit(X_tr, y_tr)
            rf_oof[test_idx] = rf.predict(X_te)

            lr = LinearRegression()
            lr.fit(X_tr, y_tr)
            lr_oof[test_idx] = lr.predict(X_te)

        rf_r2.append(float(r2_score(y, rf_oof)))
        rf_mae.append(float(mean_absolute_error(y, rf_oof)))
        lr_r2.append(float(r2_score(y, lr_oof)))
        lr_mae.append(float(mean_absolute_error(y, lr_oof)))

        rf_oof_accum[s_idx] = rf_oof
        lr_oof_accum[s_idx] = lr_oof

    rf_stats = {
        "r2_mean": float(np.mean(rf_r2)),
        "r2_std": float(np.std(rf_r2)),
        "mae_mean": float(np.mean(rf_mae)),
        "mae_std": float(np.std(rf_mae)),
    }
    lr_stats = {
        "r2_mean": float(np.mean(lr_r2)),
        "r2_std": float(np.std(lr_r2)),
        "mae_mean": float(np.mean(lr_mae)),
        "mae_std": float(np.std(lr_mae)),
    }
    return rf_stats, lr_stats, rf_oof_accum.mean(axis=0), lr_oof_accum.mean(axis=0)


def _evaluate_grouped_cv(
    df: pd.DataFrame,
    X: np.ndarray,
    y: np.ndarray,
    seed: int = 42,
) -> tuple[dict[str, float], dict[str, float]]:
    """Hard generalization test grouped by unseen (payload, speed, altitude) setting."""
    groups = (
        df["payload_g"].astype(str)
        + "_"
        + df["speed_mps"].astype(str)
        + "_"
        + df["altitude_m"].astype(str)
    )
    n_groups = int(groups.nunique())
    n_splits = min(N_SPLITS, n_groups)
    if n_splits < 2:
        nan_stats = {"r2": float("nan"), "mae": float("nan"), "n_groups": n_groups}
        return nan_stats, nan_stats

    gkf = GroupKFold(n_splits=n_splits)
    rf_oof = np.empty(len(y), dtype=float)
    lr_oof = np.empty(len(y), dtype=float)

    for train_idx, test_idx in gkf.split(X, y, groups=groups):
        X_tr, y_tr = X[train_idx], y[train_idx]
        X_te = X[test_idx]

        rf = _make_rf(seed)
        rf.fit(X_tr, y_tr)
        rf_oof[test_idx] = rf.predict(X_te)

        lr = LinearRegression()
        lr.fit(X_tr, y_tr)
        lr_oof[test_idx] = lr.predict(X_te)

    rf_grouped = {
        "r2": float(r2_score(y, rf_oof)),
        "mae": float(mean_absolute_error(y, rf_oof)),
        "n_groups": n_groups,
    }
    lr_grouped = {
        "r2": float(r2_score(y, lr_oof)),
        "mae": float(mean_absolute_error(y, lr_oof)),
        "n_groups": n_groups,
    }
    return rf_grouped, lr_grouped


def _compute_permutation_importance(
    X: np.ndarray,
    y: np.ndarray,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Compute permutation importance for Random Forest on the R1 dataset."""
    rf = _make_rf(seed)
    rf.fit(X, y)
    perm = permutation_importance(
        rf,
        X,
        y,
        n_repeats=20,
        random_state=seed,
        scoring="r2",
    )
    rows = []
    for idx, feat in enumerate(REGRESSOR_FEATURES):
        rows.append(
            {
                "feature": feat,
                "importance_mean": float(perm.importances_mean[idx]),
                "importance_std": float(perm.importances_std[idx]),
            }
        )
    rows.sort(key=lambda r: r["importance_mean"], reverse=True)
    return rows


def run_cruise_power_regression(
    flights: pd.DataFrame,
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    n_splits: int = N_SPLITS,
) -> RegressionArtifacts:
    """Train and evaluate RF vs Linear Regression for Task C3."""
    df = _prepare_r1_dataset(flights)
    X = df[list(REGRESSOR_FEATURES)].to_numpy(dtype=float)
    y = df[TARGET_COL].to_numpy(dtype=float)

    rf_cv, lr_cv, rf_oof, lr_oof = _evaluate_repeated_kfold(X, y, seeds=seeds, n_splits=n_splits)
    rf_grouped, lr_grouped = _evaluate_grouped_cv(df, X, y, seed=42)
    perm_imp = _compute_permutation_importance(X, y, seed=42)

    pred_df = pd.DataFrame(
        {
            "flight": df["flight"].astype(int),
            "observed_cruise_power_w": y,
            "rf_pred_cruise_power_w": rf_oof,
            "linear_pred_cruise_power_w": lr_oof,
        }
    )

    metrics: dict[str, Any] = {
        "target": TARGET_COL,
        "features": list(REGRESSOR_FEATURES),
        "n_flights": int(len(df)),
        "cv_folds": int(n_splits),
        "cv_seeds": list(seeds),
        "random_forest": {
            "cv": rf_cv,
            "grouped_cv": rf_grouped,
        },
        "linear_regression": {
            "cv": lr_cv,
            "grouped_cv": lr_grouped,
        },
        "permutation_importance": perm_imp,
    }
    return RegressionArtifacts(predictions=pred_df, metrics=metrics)


def build_and_save_artifacts(
    flights: pd.DataFrame | None = None,
    output_dir: Path | str = Path("data/processed"),
) -> RegressionArtifacts:
    """Run regression and persist ml_payload.parquet and ml_metrics.json."""
    if flights is None:
        flights = loader.load_table("flights")

    artifacts = run_cruise_power_regression(flights)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    expected_cols = [c.name for c in schema.ML_PAYLOAD.columns]
    pred_to_save = artifacts.predictions.copy()
    if set(expected_cols) != set(pred_to_save.columns):
        rename_map = {}
        for col in expected_cols:
            if col in pred_to_save.columns:
                continue
            if "obs" in col:
                rename_map["observed_cruise_power_w"] = col
            elif "rf" in col:
                rename_map["rf_pred_cruise_power_w"] = col
            elif "lin" in col:
                rename_map["linear_pred_cruise_power_w"] = col
        pred_to_save = pred_to_save.rename(columns=rename_map)[expected_cols]

    validated_df = loader.validate(pred_to_save, schema.ML_PAYLOAD)
    validated_df.to_parquet(out_path / "ml_payload.parquet", index=False)

    metrics_json = json.dumps(artifacts.metrics, indent=2)
    (out_path / "ml_metrics.json").write_text(metrics_json, encoding="utf-8")

    return RegressionArtifacts(predictions=validated_df, metrics=artifacts.metrics)


if __name__ == "__main__":
    result = build_and_save_artifacts()
    print(json.dumps(result.metrics, indent=2))
