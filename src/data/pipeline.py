"""Data pipeline: raw CMU files -> the contract tables the app reads (owner: Platform).

    python -m src.data.pipeline               # whole pipeline, needs data/raw/
    python -m src.data.pipeline --skip-clean  # reuse data/intermediate/ from an earlier run

Steps
1. Cleaning (Data, ``src/data/build_processed.py``): raw files -> ``data/intermediate/``.
2. Phases (Platform, ``src/data/phases.py``): phase columns and the phase tables.
3. Contract check and write (this file): every table is validated against
   ``src/data/schema.py`` and written to ``data/processed/`` under its contract file name.

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


def run(clean: bool = True, intermediate: Path = INTERMEDIATE, processed: Path = PROCESSED) -> None:
    if clean:
        build_processed.build()
    tables = assemble(read_intermediate(intermediate))
    write(tables, processed)
    report(tables)
    print(f"Contract tables written to: {processed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--skip-clean",
        action="store_true",
        help="reuse data/intermediate/ instead of rebuilding it from data/raw/",
    )
    args = parser.parse_args()
    run(clean=not args.skip_clean)
