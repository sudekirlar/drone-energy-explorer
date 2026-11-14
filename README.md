# Drone Delivery Energy Explorer

**Live app:** https://data-energy-explorer.streamlit.app/

CEN445 Introduction to Data Visualization · Çukurova University · Fall 2026
Team: Sude Kırlar, İlayda Demir, Pelin Gül Kızılkılıç

> How do payload, cruise speed and altitude shape the energy a delivery drone spends,
> and where in the flight does that energy go?

An interactive Streamlit dashboard built from 209 recordings (196 analyzed flights) of a DJI Matrice 100 package-delivery
quadcopter, recorded by Carnegie Mellon University in 2019.

_This README is a skeleton. Sections marked TODO are filled in during the week._

---

## Dataset

Rodrigues, T. A. et al. (2021). *In-flight positional and energy use data set of a DJI Matrice 100
quadcopter for small package delivery.* Scientific Data 8, 155.
https://doi.org/10.1038/s41597-021-00930-x

Data: Carnegie Mellon University, KiltHub. https://doi.org/10.1184/R1/12683453 · licence CC BY 4.0.

The raw files (`flights.csv` ≈ 102 MB) are not in this repository because they exceed GitHub's
100 MB limit. See [`data/raw/README.md`](data/raw/README.md) for how to get them.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate                 # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
streamlit run app.py
```

Requires Python 3.13.

## Repository layout

```
app.py              entry point: menu, sidebar filters, sections (UI layer)
src/sections/       one file per dashboard section (UI layer, Streamlit)
src/charts/         one file per chart, returns a Plotly figure (no Streamlit)
src/data/           contract, loading, filtering, preprocessing (no Streamlit)
src/ml/             K-means and Random Forest (no Streamlit)
data/processed/     clean tables the app reads
data/sample/        small tables with the same columns, for development
tests/              data and architecture tests
docs/               decisions, model card, user test
```

## Visualizations

TODO: finish the complete ten-chart table with all three contributors.

### Flight & Temporal Analysis — İlayda Demir

| Chart | Question | Interaction |
|---|---|---|
| G1 — Flight routes | Where did the drone fly, and how did power, speed, altitude or estimated phase change along its route? | Choose a route and up to two flights, compare matched colour scales, zoom and inspect positions. |
| G2 — Space–time cube | How do position, elapsed time and altitude relate? | Rotate the 3D scene, compare up to four flights and change the vertical axis or colour measure. |
| G3 — Inside one flight | How do power, speed, altitude and battery voltage vary throughout a flight? | Choose a flight, use linked time panels, hover and toggle estimated phase bands. |

The route map sends selected flights to the 3D cube or to the timeline.
Phase and waypoint labels are algorithmic estimates rather than hand-annotated ground truth.

## Data cleaning

The CMU data set contains 209 recordings. This dashboard analyzes the 196 flights on
routes R1–R7, excluding ground-only and stationary hover tests.

- **Power:** battery voltage multiplied by current; negative current values are clipped to zero.
- **Energy:** trapezoidal integration of power at the original sampling rate, before telemetry is resampled to 1 Hz.
- **Flight-level summaries:** duration, GPS distance, energy (Wh), energy intensity (Wh/km) and related flight measures.
- **Time corrections:** four inferred clock corrections; the original recorded values are retained.
- **Outliers:** 15 flights are flagged by the implemented joint-deviation rule, but are not removed automatically. Users can hide them with the global filter.
- **Provenance:** rule counts and ISO/IEC 25012 quality notes are presented in the Overview section.

The earlier D4 prototype reported four outliers using a different definition. These counts
must not be treated as equivalent. See [DATASHEET.md](DATASHEET.md) for provenance,
limitations and validation. Estimated phases and waypoint markers are produced by the
Platform pipeline from the cleaned telemetry.

## Chart evaluation (Q3 - RUSTIC framework)

Each of the ten dashboard charts (G1-G10) is rated on a 1-5 scale using the course RUSTIC framework:

- **R - Readable:** clear layout, legible labels, minimal overlap or crossing.
- **U - Understandable:** intuitive axes, units, legends, and visual encodings.
- **S - Supportive:** directly helps answer the flight-energy research questions.
- **T - Truthful:** honest scales, explicit cut-axis notes, and valid statistical framing.
- **I - Insightful:** reveals non-obvious patterns, interactions, or anomalies.
- **C - Communicative:** clear titles, captions, and dynamic data-driven takeaways.

| Chart | R | U | S | T | I | C | Short note |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **G1 - Flight routes** | 5 | 5 | 5 | 5 | 4 | 5 | Matched colour scales across two flights and direct send-to-3D/timeline linking. |
| **G2 - Space-time cube** | 3 | 4 | 5 | 4 | 5 | 4 | Time-by-default vertical axis earns 3D (D2); perspective occlusion mitigated by 4-flight cap. |
| **G3 - Inside one flight** | 4 | 5 | 5 | 5 | 5 | 5 | Synchronized multi-panel telemetry with phase bands and anemometer airspeed separation (D3). |
| **G4 - Energy budget Sankey** | 3 | 4 | 5 | 5 | 4 | 4 | Shows phase-to-energy flow across the mission; crossing bands reduce readability in dense splits. |
| **G5 - Experiment treemap / icicle / sunburst** | 3 | 4 | 4 | 5 | 4 | 4 | Balanced design gives near-equal box sizes, so colour hue carries the energy intensity result. |
| **G6 - Payload x speed heatmap (RF views)** | 5 | 4 | 5 | 5 | 5 | 5 | Observed, Random Forest predicted, and residual views expose non-linear speed scaling (D5). |
| **G7 - Parallel coordinates & K-means clusters** | 3 | 4 | 4 | 5 | 4 | 4 | 9 metric axes plus the group axis overlap on 181 flights; axis brushing and shared `kmeans_k` isolate clusters. |
| **G8 - Lower-triangle SPLOM** | 4 | 4 | 4 | 5 | 4 | 4 | Lower-triangle layout removes duplicate panels; `opacity=0.8` and internal box brushing highlight clusters. |
| **G9 - Power by phase and payload (violin)** | 4 | 5 | 5 | 4 | 5 | 5 | Monochromatic payload shades compare 4 phases x 3 payloads; cut Y-axis is explicitly annotated. |
| **G10 - Flight x time heatmap** | 4 | 4 | 5 | 5 | 5 | 4 | Replaces sparse calendar heatmap (D1); 2 s slices and group separators show climb-band widening. |

### What we did about weak criteria

- **3D occlusion & crossing bands (G2 & G4, R = 3):** Set G2's vertical axis to elapsed time by default (`D2`), removed the redundant top-down preset, and capped overlays at four flights.
- **High-density overplotting (G7 & G8, R = 3-4):** Restricted G8 to the lower triangle (`diagonal_visible=False`), set marker opacity to `0.8` with internal box selection, and hid individual points by default in G9 behind a `Show flight points` checkbox.
- **Near-equal hierarchy tiles & sparse calendar cells (G5 & G10):** Relied on perceptually uniform viridis colour encoding in G5 where balanced factorial cell counts yield similar box areas, and replaced the sparse 214-day calendar heatmap with a dense 181-flight x 2 s telemetry heatmap (`D1`).
- **Cut-axis honesty (G9, T = 4):** Added an explicit on-chart note whenever the power Y-axis starts above 0 W so baseline differences are not visually exaggerated.


## Machine learning

TODO: K-means clustering and Random Forest regression, evaluation and limitations.

## Contributions

TODO: complete the contributions of the other team members.

### İlayda Demir — Data & Flight Analysis

- Prepared flight telemetry, flight-level summaries, original-rate energy integration and quality logs.
- Prepared contract-compatible sample tables, automated data tests and [DATASHEET.md](DATASHEET.md).
- Built G1 (route maps), G2 (3D space–time cube) and G3 (synchronized telemetry timeline).
- Connected flight selections between the map, 3D view and timeline.
- Implemented the Overview data-quality content and contributed validation checks.

Process rules: [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

Code: MIT (see [LICENSE](LICENSE)). Data: CC BY 4.0, © the original authors.
