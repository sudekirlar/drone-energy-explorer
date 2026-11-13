# DATASHEET — CMU Drone Delivery Energy Explorer (Data role)

## Origin, purpose and license
- Source: Rodrigues et al., *In-flight positional and energy use data set of a DJI Matrice 100 quadcopter for small package delivery* (Scientific Data, 2021).
- Dataset DOI: https://doi.org/10.1184/R1/12683453 ; article DOI: https://doi.org/10.1038/s41597-021-00930-x .
- License: CC BY 4.0; credit the original authors. Recorded in controlled experiments with one DJI Matrice 100, not a representative fleet.
- Goal: explore how payload, target speed and altitude relate to flight energy, and where energy is consumed along a route.

## Composition and processing
- Original dataset contains 209 flight/ground/hover records; the selected flight analysis retains **196** flights on R1–R7 and excludes ground/hover tests.
- Local T2 output: **37,271** 1-Hz telemetry rows, plus original-rate telemetry for phase-aware energy integration.
- Voltage × nonnegative current gives power (W); trapezoidal integration at the raw sampling rate gives energy (Wh). GPS samples give travelled distance. R7 variable-altitude profiles have no single target altitude.
- The T5 examples in `data/sample/` contain **17 real flights** and **2,613 measured 1-Hz rows**, chosen for UI development, not statistical inference.
- **IMPORTANT: `data/sample/` has mock-only values in Platform-owned columns** (`cruise_power_w`, `climb_power_w`, `wp_turn_count`, `t_since_takeoff_s`, `phase`, `sub_phase`). Zeros and `Ground` there are contract placeholders, **not measured or inferred flight phases**. Never report phase energy, waypoint counts or ML predictions from these examples. Replace them with Platform-produced processed data before presenting final phase findings. This example set is marked 'sample data' by the app.
- `data/processed/quality_log.json` is a real cleaning log, not a mock.

## Data quality and known limitations
- Four local-time transcription corrections are inferred from nearby flight timestamps, not independently verified; originals are retained.
- Negative battery current readings are clipped to zero. Missing values and time gaps may affect the dataset and must not be filled with fabricated sensor readings.
- Outlier algorithm flags **15** flights by a documented joint-deviation rule, while prototype D4 reported 4 under an unspecified formula; the figures are not interchangeable. Flagged flights are retained.
- Airspeed (`wind_speed` in the raw file) is an anemometer measurement, **not an independent environmental wind-speed variable**.
- Experiment settings and R1 routes are more comparable than R2–R7. R6/R7 and other routes have fewer runs, and results should not be generalized to other UAVs or operational conditions.
- Phase labels are algorithmic estimates owned by Platform and have no hand-annotated ground truth; inspect sensitivity and energy-conservation checks before using them.

## Reproducibility and validation
- `python -m src.data.build_processed` builds Data-owned intermediates from separately downloaded source CSVs under `data/raw/`.
- `python -m src.data.build_samples` validates them and exports the mock-labeled T5 examples and this Datasheet.
- T3 checks include unique keys, positive durations, nonnegative energy, contract validation and raw-rate energy reconciliation where the raw-rate file is present.
- Raw-rate maximum absolute integration discrepancy: **0.00000000 Wh**.
- Final **phase-energy conservation, phase completeness and turn-count thresholds depend on T6 outputs and must be tested once Platform publishes them**.
