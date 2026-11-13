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

## Chart evaluation (Q3 ? 6-criteria framework)

Each of the ten dashboard charts (G1?G10) is rated on a 1?5 scale across the six course evaluation criteria:

1. **Task fit** ? answers a concrete analytical question for the flight-energy domain.
2. **Data integrity** ? preserves true units, unclipped scales, or explicit cut-axis notes.
3. **Visual encoding** ? matches variable types to position, length, angle, or hue (Lecture 3?5).
4. **Clutter control** ? avoids overplotting, unreadable labels, and empty cells (Lecture 5?7).
5. **Interaction** ? provides filtering, view switching, or cross-chart linking where earned.
6. **Colour safety** ? uses colourblind-safe palettes and consistent semantics across views.

| Chart | Task fit | Data integrity | Visual encoding | Clutter control | Interaction | Colour safety | Short note |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **G1 ? Flight routes** | 5 | 5 | 5 | 4 | 5 | 5 | Matched colour scales across two flights and direct send-to-3D/timeline linking. |
| **G2 ? Space?time cube** | 5 | 4 | 4 | 3 | 5 | 5 | Earns 3D via time-by-default vertical axis (D2); 3D perspective/occlusion mitigated by 4-flight cap. |
| **G3 ? Inside one flight** | 5 | 5 | 5 | 4 | 5 | 5 | Synchronized multi-panel time series with phase bands and anemometer airspeed separation (D3). |
| **G4 ? Energy & power overview** | 5 | 5 | 5 | 5 | 4 | 5 | Clear baseline distribution across R1 configurations with joint-deviation outlier toggle (D4). |
| **G5 ? Factor effects (speed ? altitude ? payload)** | 5 | 5 | 5 | 4 | 4 | 5 | Small-multiples layout separates payload and altitude interactions without 3D distortion. |
| **G6 ? Cruise power regression (RF vs Linear)** | 5 | 5 | 5 | 4 | 5 | 5 | Observed, predicted, and residual views expose non-linear speed scaling directly (D5). |
| **G7 ? Parallel coordinates & K-means clusters** | 4 | 5 | 4 | 3 | 5 | 5 | Polylines across 6 metrics can overlap on 181 flights; brush filters and shared `kmeans_k` isolate clusters. |
| **G8 ? Lower-triangle scatter-plot matrix (SPLOM)** | 4 | 5 | 5 | 3 | 5 | 5 | Lower-triangle layout removes duplicate panels; `opacity=0.65` and box/lasso selection link to G7. |
| **G9 ? Power by phase and payload (violin)** | 5 | 4 | 5 | 4 | 4 | 5 | Monochromatic payload shades compare 4 phases ? 3 payloads; cut Y-axis is explicitly annotated. |
| **G10 ? Flight ? time heatmap** | 5 | 5 | 4 | 4 | 5 | 5 | Replaces sparse calendar heatmap (D1); 2 s slices and group separators reveal climb-band widening. |

### What we did about weak criteria

- **3D occlusion & clutter (G2, score 3/5 in clutter control):** Set the vertical axis to elapsed time by default (`D2`), removed the redundant top-down preset, and capped overlays at four flights.
- **Overplotting in high-density multivariate views (G7 & G8, score 3/5 in clutter control):** Restricted G8 to the lower triangle (`diagonal_visible=False`), used `opacity=0.65`, hid individual points by default in G9 behind a `Show flight points` checkbox, and added brush/lasso selection linking between G7 and G8.
- **Sparse matrix cells (G10, replacing calendar heatmap):** Replaced the 214-day calendar heatmap (only 16 active days) with a dense 181-flight ? 2 s telemetry heatmap sortable by altitude, speed, payload, or K-means cluster (`D1`).
- **Cut-axis honesty (G9, score 4/5 in data integrity):** Added an explicit on-chart annotation whenever the power Y-axis starts above 0 W so baseline differences are not visually exaggerated.

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
