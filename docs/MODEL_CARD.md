# Model Card — Cruise Power Regressor (`cruise_power_w`)

## Purpose, Data & Features
- **Purpose:** Estimate steady-state drone cruise power (`cruise_power_w`, W) from planned mission settings (`D5`) and compare non-linear tree predictions against an Ordinary Least Squares (OLS) baseline in Chart G6.
- **Training Data:** 181 R1 design flights (`in_design == True`) from the CMU DJI Matrice 100 package-delivery dataset (209 total recordings; ground/hover tests excluded, R2–R7 held out from training).
- **Features & Target:** Controlled mission parameters `payload_g` (0–500 g), `speed_mps` (4–12 m/s), and `altitude_m` (25–100 m) predicting `cruise_power_w` (W). Anemometer airspeed is excluded (`D3`) because it tracks ground speed rather than ambient wind.

## Evaluation Results (5-Fold CV × 5 Seeds & Grouped Configuration Test)
Metrics computed in `src/ml/regressor.py` (`data/processed/ml_metrics.json`):

| Model | 5-Fold CV $R^2$ (mean ± std) | 5-Fold CV MAE (W, mean ± std) | Grouped CV $R^2$ (60 configs) | Grouped CV MAE (W) |
|---|:---:|:---:|:---:|:---:|
| **Random Forest** | **0.788 ± 0.008** | **14.91 ± 0.33** | **0.760** | **15.42** |
| **Linear Regression (OLS)** | 0.772 ± 0.001 | 15.42 ± 0.03 | 0.746 | 16.08 |

- **Feature Importance:** Permutation importance is dominated by `payload_g` (`1.587 ± 0.129`), followed by `speed_mps` (`0.058 ± 0.036`) and `altitude_m` (`0.014 ± 0.014`).
- **Generalization:** Grouping folds by the 60 `(payload_g, speed_mps, altitude_m)` configurations prevents repeat-flight leakage; Random Forest retains a +0.013 $R^2$ and −0.66 W MAE advantage on unseen combinations.

## Limitations & Responsible Use
- **R6 Route Shift:** Trained exclusively on R1 triangular flights; routes with continuous climbs or tighter turns (such as R6/R7) exhibit systematic distribution shifts in power draw.
- **Single Airframe (DJI Matrice 100):** Valid only for the DJI Matrice 100 quadcopter under the recorded battery, propeller, and weather conditions; do not extrapolate to other airframes or payloads above 500 g.
- **Association, Not Causation:** Model weights reflect empirical associations within the experimental grid and isolate cruise power only, omitting take-off, landing, and ambient wind energy costs.
