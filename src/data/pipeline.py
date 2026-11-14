"""Data pipeline: raw CMU files -> the contract tables the app reads (owner: Platform).

    python -m src.data.pipeline               # whole pipeline, needs data/raw/
    python -m src.data.pipeline --skip-clean  # reuse data/intermediate/ from an earlier run
    python -m src.data.pipeline --skip-model  # leave ml_payload and ml_metrics.json as they are

Steps
1. Cleaning (Data, ``src/data/build_processed.py``): raw files -> ``data/intermediate/``.
2. Phases (Platform, ``src/data/phases.py``): phase columns and the phase tables.
3. Contract check and write (this file): every table is validated against
   ``src/data/schema.py`` and written to ``data/processed/`` under its contract file name.
4. Model (UI & ML, ``src/ml/regressor.py``): the Random Forest and linear regression are
   evaluated again on the new ``flights`` table, and ``ml_payload`` and ``ml_metrics.json`` are
   rewritten. Without this step a rebuilt ``flights`` table would sit next to predictions made
   from the old one. It takes about half a minute (5-fold cross-validation, 5 seeds).

This is the only module that writes ``data/processed/``. The files there are committed to git,
because Streamlit Cloud has no raw data; rerun this script and commit them again whenever a
producer changes.

No Streamlit here (see tests/test_architecture.py).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.data import build_processed, loader, phases, schema
from src.ml import regressor

INTERMEDIATE = Path("data/intermediate")
PROCESSED = Path("data/processed")


def read_intermediate(intermediate: Path = INTERMEDIATE) -> dict[str, pd.DataFrame]:
    """The tables written by the cleaning step."""
    return {
        "raw": pd.read_parquet(intermediate / "raw_rate_telemetry.parquet"),
        "flights": pd.read_parquet(intermediate / "flights_data.parquet"),
        "telemetry_1hz": pd.read_parquet(intermediate / "telemetry_data_1hz.parquet"),
        "quality_log": pd.DataFrame(
            json.loads((intermediate / "quality_log.json").read_text(encoding="utf-8"))
        ),
    }


def assemble(inputs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Add the phase columns and tables, then check every table against the contract."""
    labelled, energy, waypoints, summary = phases.label_all(inputs["raw"], inputs["flights"])

    flights = (
        inputs["flights"]
        .drop(columns=phases.PLATFORM_FLIGHT_COLUMNS, errors="ignore")
        .merge(summary, on="flight", how="left", validate="one_to_one")
    )
    tables = {
        "flights": flights,
        "telemetry_1hz": phases.add_phases_to_1hz(inputs["telemetry_1hz"], labelled),
        "phase_energy": energy,
        "waypoints": waypoints,
        "quality_log": inputs["quality_log"],
    }
    return {name: loader.validate(df, schema.TABLES[name]) for name, df in tables.items()}


def write(tables: dict[str, pd.DataFrame], processed: Path = PROCESSED) -> None:
    """Write each table to data/processed under the file name the contract gives it."""
    processed.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        path = processed / schema.TABLES[name].filename
        if path.suffix == ".json":
            records = df.to_dict(orient="records")
            path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
        else:
            df.to_parquet(path, index=False)


def report(tables: dict[str, pd.DataFrame]) -> None:
    """Print the checks of D6 and D14, so every build shows whether the phase rule still holds."""
    flights = tables["flights"]
    total = flights.set_index("flight")["energy_wh"]
    gap = (tables["phase_energy"].groupby("flight")["energy_wh"].sum() - total).abs().max()
    design = flights.loc[flights["in_design"]]
    two_turns = int((design["wp_turn_count"] == 2).sum())
    print(f"Flights: {len(flights)}")
    print(f"Largest gap between phase energies and total energy: {gap:.1e} Wh")
    print(f"R1 design flights with exactly two WP turns: {two_turns} of {len(design)}")


def write_model(flights: pd.DataFrame, processed: Path = PROCESSED) -> dict:
    """Re-evaluate the cruise power models on ``flights`` and write their two output files.

    The model code is UI & ML's (src/ml/regressor.py); this step only makes sure it runs on the
    same flights table that was just written, and prints the headline scores.
    """
    metrics = regressor.build_and_save_artifacts(flights=flights, output_dir=processed).metrics
    rf, lin = metrics["random_forest"]["cv"], metrics["linear_regression"]["cv"]
    print(f"Random Forest R2 {rf['r2_mean']:.3f}, linear R2 {lin['r2_mean']:.3f}")
    return metrics


def run(
    clean: bool = True,
    model: bool = True,
    intermediate: Path = INTERMEDIATE,
    processed: Path = PROCESSED,
) -> None:
    if clean:
        build_processed.build()
    tables = assemble(read_intermediate(intermediate))
    write(tables, processed)
    report(tables)
    if model:
        write_model(tables["flights"], processed)
    print(f"Contract tables written to: {processed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--skip-clean",
        action="store_true",
        help="reuse data/intermediate/ instead of rebuilding it from data/raw/",
    )
    parser.add_argument(
        "--skip-model",
        action="store_true",
        help="do not re-evaluate the regression models (ml_payload, ml_metrics.json)",
    )
    args = parser.parse_args()
    run(clean=not args.skip_clean, model=not args.skip_model)
