# ruff: noqa: E501
"""T5: export small real-data contract examples without calculating Platform/ML results.

Run from repository root: python -m src.data.build_samples
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.data import loader, schema

ROOT = Path(__file__).resolve().parents[2]
INTERMEDIATE = ROOT / "data" / "intermediate"
SAMPLE = ROOT / "data" / "sample"
PROCESSED = ROOT / "data" / "processed"


def choose_flights(flights: pd.DataFrame) -> list[int]:
    """15 R1 flights spanning experimental levels, plus R6 and R7 if present."""
    r1 = flights.loc[(flights["route"] == "R1") & flights["in_design"]].copy()
    r1 = r1.sort_values("flight")
    if r1.empty:
        raise ValueError("No eligible R1 experiment flights found")
    keys = ("payload_g", "altitude_m", "speed_mps")
    seen: set[tuple[str, str]] = set()
    chosen: list[int] = []
    remaining = r1.to_dict("records")
    while remaining and len(chosen) < 15:

        def score(row: dict) -> tuple[int, int]:
            coverage = {(key, str(row[key])) for key in keys}
            return len(coverage - seen), -int(row["flight"])

        best = max(remaining, key=score)
        chosen.append(int(best["flight"]))
        seen.update((key, str(best[key])) for key in keys)
        remaining.remove(best)
    for route in ("R6", "R7"):
        candidates = flights.loc[flights["route"] == route, "flight"]
        if not candidates.empty:
            chosen.append(int(candidates.iloc[0]))
    return chosen


def build_sample_frames(
    flights: pd.DataFrame, telemetry: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retain measurements; mark unavailable Platform-owned fields as mock-only."""
    ids = choose_flights(flights)
    example_flights = flights.loc[flights["flight"].isin(ids)].copy()
    example_telemetry = telemetry.loc[telemetry["flight"].isin(ids)].copy()
    if example_telemetry.empty:
        raise ValueError("Selected flights have no telemetry")

    # These fields are owned by Platform (T6), *not* estimates computed here.
    # Placeholder values exist ONLY in data/sample/ to satisfy schema v1.
    example_flights["cruise_power_w"] = 0.0
    example_flights["climb_power_w"] = 0.0
    example_flights["wp_turn_count"] = 0
    example_telemetry["t_since_takeoff_s"] = 0.0
    example_telemetry["phase"] = "Ground"
    example_telemetry["sub_phase"] = "Ground"

    # Select only actual measured samples with complete Data-owned fields.
    required = [
        c.name for c in schema.TELEMETRY.columns if c.producer == schema.DATA and not c.nullable
    ]
    example_telemetry = example_telemetry.dropna(subset=required)
    kept = set(example_telemetry["flight"])
    example_flights = example_flights.loc[example_flights["flight"].isin(kept)]
    flight_required = [
        c.name for c in schema.FLIGHTS.columns if c.producer == schema.DATA and not c.nullable
    ]
    example_flights = example_flights.dropna(subset=flight_required)
    example_telemetry = example_telemetry.loc[
        example_telemetry["flight"].isin(example_flights["flight"])
    ]
    if example_flights.empty or example_telemetry.empty:
        raise ValueError("No complete data remained after checking measurements")
    # Do not turn a data error into invented sensor readings.
    example_flights = loader.validate(example_flights, schema.FLIGHTS)
    example_telemetry = loader.validate(example_telemetry, schema.TELEMETRY)
    return example_flights, example_telemetry


def validate_energy(flights: pd.DataFrame, raw_rate: pd.DataFrame) -> float:
    """T3: raw-rate integrated Wh must equal flight-summary Wh for every flight."""
    last = raw_rate.sort_values(["flight", "t_s"]).groupby("flight")["energy_wh"].last()
    expected = flights.set_index("flight")["energy_wh"]
    if set(last.index) != set(expected.index):
        raise ValueError("Raw-rate and summary flight IDs differ")
    actual = last.loc[expected.index].to_numpy(dtype=float)
    wanted = expected.to_numpy(dtype=float)
    if not np.isfinite(actual).all() or not np.isfinite(wanted).all():
        raise ValueError("Non-finite flight energy in pipeline")
    differences = np.abs(actual - wanted)
    if not np.allclose(actual, wanted, rtol=1e-7, atol=1e-6):
        bad = expected.index[differences > 1e-6].tolist()[:10]
        raise ValueError(f"T3 energy conservation failed for flights: {bad}")
    if (raw_rate["current_a"] < 0).any() or (raw_rate["power_w"] < 0).any():
        raise ValueError("Negative cleaned current or power detected")
    return float(differences.max())


def build() -> None:
    file_names = ("flights_data.parquet", "telemetry_data_1hz.parquet", "quality_log.json")
    missing = [n for n in file_names if not (INTERMEDIATE / n).exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing intermediate files: {missing}. First run: python -m src.data.build_processed"
        )

    flights = pd.read_parquet(INTERMEDIATE / "flights_data.parquet")
    telemetry = pd.read_parquet(INTERMEDIATE / "telemetry_data_1hz.parquet")
    quality = json.loads((INTERMEDIATE / "quality_log.json").read_text(encoding="utf-8"))
    loader.validate(pd.DataFrame(quality), schema.QUALITY_LOG)
    # First validate the real producer's Data-owned results before exporting samples.
    if flights["flight"].nunique() != 196:
        raise ValueError(f"Expected 196 flight records, found {flights['flight'].nunique()}")
    if flights["flight"].duplicated().any() or telemetry.duplicated(["flight", "t_s"]).any():
        raise ValueError("Flight or telemetry keys are not unique")
    if not ((flights["duration_s"] > 0).all() and (flights["energy_wh"] >= 0).all()):
        raise ValueError("Invalid flight duration or energy")

    # T3 raw-rate integration, if the T2 patch output exists locally.
    max_energy_difference = None
    raw_rate_file = INTERMEDIATE / "raw_rate_telemetry.parquet"
    if raw_rate_file.exists():
        max_energy_difference = validate_energy(flights, pd.read_parquet(raw_rate_file))

    sample_flights, sample_telemetry = build_sample_frames(flights, telemetry)
    SAMPLE.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    sample_flights.to_parquet(SAMPLE / "flights.parquet", index=False)
    sample_telemetry.to_parquet(SAMPLE / "telemetry_1hz.parquet", index=False)
    (SAMPLE / "quality_log.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")
    # Quality log is a genuine Data-owned output, unlike the sample phase placeholders.
    (PROCESSED / "quality_log.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")
    for name in ("flights", "telemetry_1hz", "quality_log"):
        loader.load_table(name)

    doc = f"""# DATASHEET — CMU Drone Delivery Energy Explorer (Data role)

## Origin, purpose and license
- Source: Rodrigues et al., *In-flight positional and energy use data set of a DJI Matrice 100 quadcopter for small package delivery* (Scientific Data, 2021).
- Dataset DOI: https://doi.org/10.1184/R1/12683453 ; article DOI: https://doi.org/10.1038/s41597-021-00930-x .
- License: CC BY 4.0; credit the original authors. Recorded in controlled experiments with one DJI Matrice 100, not a representative fleet.
- Goal: explore how payload, target speed and altitude relate to flight energy, and where energy is consumed along a route.

## Composition and processing
- Original dataset contains 209 flight/ground/hover records; the selected flight analysis retains **{len(flights)}** flights on R1–R7 and excludes ground/hover tests.
- Local T2 output: **{len(telemetry):,}** 1-Hz telemetry rows, plus original-rate telemetry for phase-aware energy integration.
- Voltage × nonnegative current gives power (W); trapezoidal integration at the raw sampling rate gives energy (Wh). GPS samples give travelled distance. R7 variable-altitude profiles have no single target altitude.
- The T5 examples in `data/sample/` contain **{len(sample_flights)} real flights** and **{len(sample_telemetry):,} measured 1-Hz rows**, chosen for UI development, not statistical inference.
- **IMPORTANT: `data/sample/` has mock-only values in Platform-owned columns** (`cruise_power_w`, `climb_power_w`, `wp_turn_count`, `t_since_takeoff_s`, `phase`, `sub_phase`). Zeros and `Ground` there are contract placeholders, **not measured or inferred flight phases**. Never report phase energy, waypoint counts or ML predictions from these examples. Replace them with Platform-produced processed data before presenting final phase findings. This example set is marked 'sample data' by the app.
- `data/processed/quality_log.json` is a real cleaning log, not a mock.

## Data quality and known limitations
- Four local-time transcription corrections are inferred from nearby flight timestamps, not independently verified; originals are retained.
- Negative battery current readings are clipped to zero. Missing values and time gaps may affect the dataset and must not be filled with fabricated sensor readings.
- Outlier algorithm flags **{int(flights["is_outlier"].sum())}** flights by a documented joint-deviation rule, while prototype D4 reported 4 under an unspecified formula; the figures are not interchangeable. Flagged flights are retained.
- Airspeed (`wind_speed` in the raw file) is an anemometer measurement, **not an independent environmental wind-speed variable**.
- Experiment settings and R1 routes are more comparable than R2–R7. R6/R7 and other routes have fewer runs, and results should not be generalized to other UAVs or operational conditions.
- Phase labels are algorithmic estimates owned by Platform and have no hand-annotated ground truth; inspect sensitivity and energy-conservation checks before using them.

## Reproducibility and validation
- `python -m src.data.build_processed` builds Data-owned intermediates from separately downloaded source CSVs under `data/raw/`.
- `python -m src.data.build_samples` validates them and exports the mock-labeled T5 examples and this Datasheet.
- T3 checks include unique keys, positive durations, nonnegative energy, contract validation and raw-rate energy reconciliation where the raw-rate file is present.
- Raw-rate maximum absolute integration discrepancy: **{f"{max_energy_difference:.8f} Wh" if max_energy_difference is not None else "not checked: raw-rate file absent"}**.
- Final **phase-energy conservation, phase completeness and turn-count thresholds depend on T6 outputs and must be tested once Platform publishes them**.
"""
    (ROOT / "DATASHEET.md").write_text(doc, encoding="utf-8")
    print(f"T5 ready: {len(sample_flights)} real sample flights, {len(sample_telemetry)} rows")
    print("T3: unique keys, data contract and basic numeric checks PASS")
    energy_status = (
        f"PASS, max difference {max_energy_difference:.8g} Wh"
        if max_energy_difference is not None
        else "NOT VERIFIED"
    )
    print(f"T3 raw-rate energy: {energy_status}")
    print("DATASHEET.md written. Platform phase fields in sample are placeholders only.")


if __name__ == "__main__":
    build()
