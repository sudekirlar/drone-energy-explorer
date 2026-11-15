# Delivery Drone Energy Explorer

**Live app:** https://delivery-drone-energy-explorer.streamlit.app/

CEN445 Introduction to Data Visualization · Çukurova University · Fall 2026
Team: Sude Kırlar, İlayda Demir, Pelin Gül Kızılkılıç

> How do payload, cruise speed and altitude shape the energy a delivery drone spends,
> and where in the flight does that energy go?

An interactive Streamlit dashboard built from 209 recordings (196 analyzed flights) of a DJI Matrice 100 package-delivery
quadcopter, recorded by Carnegie Mellon University in 2019.

_This README is a skeleton. Sections marked TODO are filled in during the week._

## Approach (CRISP-DM)

We followed the six phases of CRISP-DM. The table shows what each phase meant in this project
and where to find it.

| Phase | What we did | Where |
|---|---|---|
| Business understanding | We asked how payload, cruise speed and altitude change the energy of a delivery drone, and in which part of the flight the energy is spent. | The question above; the Overview section |
| Data understanding | We explored the data before building any chart. We found that `wind_speed` is the drone's airspeed, not the wind, and that only 16 of the 214 days in the collection period have flights. | [Dataset](#dataset); D1 and D3 in [docs/decisions.md](docs/decisions.md) |
| Data preparation | We cleaned the telemetry, flagged outlier flights, estimated the flight phases and checked every table against a data contract. | [Data cleaning](#data-cleaning); D4, D6, D14 and D15 |
| Modeling | We grouped the flights with K-means and predicted cruise power with a Random Forest, compared with a linear model. | [Machine learning](#machine-learning); [docs/MODEL_CARD.md](docs/MODEL_CARD.md); D5 |
| Evaluation | We scored the models with cross-validation, rated every chart with RUSTIC and tested the code and the data automatically. | [Chart evaluation](#chart-evaluation-q3---rustic-framework); [Testing](#testing) |
| Deployment | The dashboard runs on Streamlit Community Cloud from the `main` branch. | The live link above; D9 |

---

## Dataset

Rodrigues, T. A. et al. (2021). *In-flight positional and energy use data set of a DJI Matrice 100
quadcopter for small package delivery.* Scientific Data 8, 155.
https://doi.org/10.1038/s41597-021-00930-x

Data: Carnegie Mellon University, KiltHub. https://doi.org/10.1184/R1/12683453 · licence CC BY 4.0.

The raw files (`flights.csv` ≈ 102 MB) are not in this repository because they exceed GitHub's
100 MB limit. See [`data/raw/README.md`](data/raw/README.md) for how to get them.

The data set has several types of data. The telemetry (`flights.csv`, 257,896 rows and 28
columns) is a time series: each row is one moment of a flight. Most of its columns are
continuous numbers, such as battery voltage and current, speed and acceleration. Position is
geographic (latitude, longitude and altitude). The flight list (`parameters.csv`, 209 rows and 7
columns) holds the settings of each flight. Payload, speed and altitude are ordered levels of
the experiment, the route (R1–R7) is a category, and the start date and time are temporal.
From these, we add more types: estimated flight phases are categories, and the settings of the
R1 experiment form a hierarchy (payload, altitude and speed), which the treemap shows.

## Run locally

You need Python 3.13 and Git. The processed tables the app reads are in the repository, so you
do not need to download the raw data to run the app.

```bash
git clone https://github.com/sudekirlar/drone-energy-explorer.git
cd drone-energy-explorer
python -m venv .venv
.venv\Scripts\activate                 # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
streamlit run app.py                   # opens the app at http://localhost:8501
```

To check the installation, run `pytest`. All tests should pass.

To rebuild the processed tables from the raw CMU files, put the files into `data/raw/` (see
[`data/raw/README.md`](data/raw/README.md)) and run `python -m src.data.pipeline`. It cleans the
telemetry, estimates the flight phases, checks every table against the data contract, writes
`data/processed/` and evaluates the regression models again.

## Repository layout

The code has three layers. `src/data`, `src/ml` and `src/charts` are plain Python and never
import Streamlit, so they can be tested without a browser. `src/sections` and `app.py` hold
everything the visitor sees. A test (`tests/test_architecture.py`) checks this rule.

```
app.py              entry point: menu, sidebar filters, sections (UI layer)
src/sections/       one file per dashboard section (UI layer, Streamlit)
src/charts/         one file per chart, returns a Plotly figure (no Streamlit)
src/data/           contract, loading, filtering, preprocessing (no Streamlit)
src/ml/             K-means and Random Forest (no Streamlit)
data/processed/     clean tables the app reads
data/sample/        small tables with the same columns, for development
tests/              data and architecture tests
docs/               decisions, interfaces, model card
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

### Energy & Experimental Conditions — Sude Kırlar

| Chart | Question | Interaction |
|---|---|---|
| G4 — Energy budget (Sankey) | Where in the flight does the energy go, and how does this change with altitude, speed, payload or route? | Group the flights by altitude, speed, payload or route, hover over a band or a node to read its energy and share, and drag a node to move it. |
| G5 — Cost of each setting (treemap, icicle, sunburst) | Which setting of the experiment uses the least energy per kilometre, and how does the order change down the tree? | Switch between the three drawings, change the order of the levels, click a box to zoom in and hover to read the median and the spread. |
| G6 — Payload, speed and cruise power (heatmap with a Random Forest) | How do payload and speed change cruise power, and where does a straight-line model fail? | Switch between measured power, the Random Forest prediction and the two differences, and compare each flight's prediction with its measurement. |

Altitude, speed and payload are compared only on the R1 flights of the experiment, because only
there are the three settings balanced. The Sankey's "Route" grouping uses every filtered flight.
The model behind G6 is described in [docs/MODEL_CARD.md](docs/MODEL_CARD.md).

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
| **G4 - Energy budget Sankey** | 3 | 4 | 5 | 4 | 5 | 5 | It shows where each group's energy goes, phase by phase. Bands cross between the groups and the phases, and the uncertainty of the estimated phases is only in the About text. |
| **G5 - Experiment treemap / icicle / sunburst** | 3 | 4 | 5 | 5 | 4 | 5 | It names the cheapest and the most expensive setting directly. The boxes are almost equal in size, so the colour (the lightness of Viridis) carries the result, and small boxes are hard to read. |
| **G6 - Payload x speed heatmap (RF views)** | 4 | 4 | 5 | 5 | 5 | 5 | The measured, predicted and difference views show that cruise power does not change in a straight line with speed (D5). The card is dense: three scores, four views and two smaller charts. |
| **G7 - Parallel coordinates & K-means clusters** | 3 | 4 | 4 | 5 | 4 | 4 | 9 metric axes plus the group axis overlap on 181 flights; axis brushing and shared `kmeans_k` isolate clusters. |
| **G8 - Lower-triangle SPLOM** | 4 | 4 | 4 | 5 | 4 | 4 | Lower-triangle layout removes duplicate panels; `opacity=0.8` and internal box brushing highlight clusters. |
| **G9 - Power by phase and payload (violin)** | 4 | 5 | 5 | 4 | 5 | 5 | Monochromatic payload shades compare 4 phases x 3 payloads; cut Y-axis is explicitly annotated. |
| **G10 - Flight x time heatmap** | 4 | 4 | 5 | 5 | 5 | 4 | Replaces sparse calendar heatmap (D1); 2 s slices and group separators show climb-band widening. |

### What we did about weak criteria

- **3D occlusion (G2, R = 3):** Set G2's vertical axis to elapsed time by default (`D2`), removed the redundant top-down preset, and capped overlays at four flights.
- **High-density overplotting (G7 & G8, R = 3-4):** Restricted G8 to the lower triangle (`diagonal_visible=False`), set marker opacity to `0.8` with internal box selection, and hid individual points by default in G9 behind a `Show flight points` checkbox.
- **Crossing bands (G4, R = 3):** The nodes have fixed positions (groups from top to bottom, phases in the order of the flight), so the layout looks the same for every grouping and is easy to compare. Every node is labelled, so colour is never the only clue, and the sub-phases sit in their own column, so the main split stays readable. The Ground phase (under 1% of any flight) is left out. With seven routes the bands still cross a lot; the Route grouping is meant to describe each route, not to rank them.
- **Estimated phases (G4, T = 4):** The data has no phase labels, so the phases come from a rule on the sensors (D6). The About text says how much the shares move when the rule's thresholds change: take-off and landing hardly move, cruise and manoeuvre can move by 2 to 4 percentage points. The bands show the mean of the flights in a group, and the spread between flights is not drawn on the chart.
- **Small boxes (G5, R = 3):** The boxes are almost equal because the experiment flew almost every setting three times, so the colour carries the result, on a scale whose lightness changes evenly (Viridis). The icicle and the sunburst open two levels deep, because 60 settings were too thin to read, and labels that do not fit are hidden rather than shrunk. The hover gives the median of every box and, from three flights up, the middle half of the flights.
- **A dense card (G6, R = 4 and U = 4):** The card holds three scores, four views and two smaller charts, and R² and feature importance are new to most readers. The scores have help texts, the two smaller charts sit side by side under the grid, and the About text explains a Random Forest, R² and the shuffling test in plain words. Both difference views share one colour scale, so they can be compared directly.
- **Sparse calendar cells (G10):** Replaced the sparse 214-day calendar heatmap with a dense 181-flight x 2 s telemetry heatmap (`D1`).
- **Cut-axis honesty (G9, T = 4):** Added an explicit on-chart note whenever the power Y-axis starts above 0 W so baseline differences are not visually exaggerated.


## Testing

The tests in `tests/` check the code and the data. CI runs the linter and every test on each pull
request and on `main`, and a pull request cannot be merged while CI fails. The tests cover:

- **The data contract:** every table has the expected columns, types, units and keys, and a broken
  table is reported by name (`test_loader.py`).
- **Cleaning:** power, energy integration at the original sampling rate, distances and time gaps
  (`test_data.py`, `test_raw_telemetry.py`).
- **Estimated phases:** the phase energies of a flight add up exactly to its total energy, and every
  flight has a row for every sub-phase (`test_phases.py`).
- **Charts:** the data shaping and the finding texts of the charts, on small synthetic tables.
- **Models:** K-means and the regression (`test_clustering.py`, `test_regressor.py`).
- **The app as a whole:** the layer rule (`test_architecture.py`) and a smoke test that opens every
  section (`test_app_smoke.py`).

## Machine learning

TODO: K-means clustering and Random Forest regression, evaluation and limitations.

## Assignment requirements

Each requirement of the assignment, where it is met, and how to check it.

| Requirement | Where | Evidence |
|---|---|---|
| A data set with at least 2,000 rows, 7 columns and varied data types | [Dataset](#dataset) | `flights.csv` has 257,896 rows and 28 columns, and `parameters.csv` has 209 rows and 7 columns. The data are numerical, categorical, ordinal, temporal and geographic. |
| Cleaning: missing values, outliers and data quality | [Data cleaning](#data-cleaning); the Overview section | Samples without a time or power reading are dropped, never filled in. 15 outlier flights are flagged (D4) and can be hidden in the sidebar. The Overview lists every cleaning rule with the number of rows it changed, and the ISO/IEC 25012 checks. |
| At least 9 visualizations, 3 per member | [Visualizations](#visualizations) | There are ten charts: G1–G3 by İlayda Demir, G4–G6 by Sude Kırlar and G7–G10 by Pelin Gül Kızılkılıç. |
| At least 6 advanced types | D7 in [docs/decisions.md](docs/decisions.md) | Seven charts are advanced types: the route map, the Sankey diagram, the treemap (with icicle and sunburst), parallel coordinates, the Space-Time Cube, the scatterplot matrix and the flight × time heatmap. |
| A unique insight in every chart | The finding box of each card | Each card answers its own question, and its finding is computed from the flights on screen. |
| Interactivity in every chart | The "Interaction" column of [Visualizations](#visualizations) | Every chart has hover texts, except the parallel coordinates, which Plotly draws without hover; there, the visitor filters by dragging along an axis. Other interactions are zooming and panning the map and the charts, dragging Sankey nodes, zooming into the tree by clicking, selecting points in the scatterplot matrix, and sending flights from the map to the cube and the timeline. |
| At least three interactive components | The sidebar and the cards | Multiselect menus filter payload, altitude and speed; checkboxes hide outlier flights and add routes R2–R7; dropdown menus change each card's view; a slider sets the number of K-means groups. |
| Labels and visual consistency | [docs/interfaces.md](docs/interfaces.md) ("Card pattern"); `src/theme.py` | Every card has the same parts in the same order. Axes have titles with units, and all colours come from one theme file. |
| Two machine-learning algorithms | [Machine learning](#machine-learning); [docs/MODEL_CARD.md](docs/MODEL_CARD.md) | K-means groups the flights (G7, shared with G8 and G10). A Random Forest regression predicts cruise power and is compared with a linear model (G6). |
| Colour schemes, legends and annotations | `src/theme.py`; D16 | Quantities use Viridis, groups use the Okabe–Ito colours, and differences use a diverging blue–red scale. A test (`tests/test_colours.py`) checks every palette under simulated colour-vision deficiencies. A cut axis is marked on the chart (G9). |
| A public GitHub repository with `app.py`, the data and a README | This repository | `app.py` is the entry point. The processed tables are in `data/processed/`, and the raw data are linked in [Dataset](#dataset). [Run locally](#run-locally) explains the setup. |
| Each member's contribution | [Contributions](#contributions) | One list per member, and every commit and review on GitHub under the member's own name. |

## Contributions

TODO: complete the contributions of the other team members.

### İlayda Demir — Data & Flight Analysis

- Prepared flight telemetry, flight-level summaries, original-rate energy integration and quality logs.
- Prepared contract-compatible sample tables, automated data tests and [DATASHEET.md](DATASHEET.md).
- Built G1 (route maps), G2 (3D space–time cube) and G3 (synchronized telemetry timeline).
- Connected flight selections between the map, 3D view and timeline.
- Implemented the Overview data-quality content and contributed validation checks.

### Sude Kırlar — Platform & Energy

- Set up the repository: its structure, pinned dependencies, linting and pre-commit checks, CI, code owners, issue and pull request templates, and the contributing guide.
- Defined the data contract for the six tables (`schema.py`) and the loader that checks every table and falls back to the sample data (`loader.py`).
- Estimated the flight phases, the energy of each phase and the waypoints from the telemetry (`phases.py`), and wrote the pipeline that checks and writes the processed tables and re-runs the regression (`pipeline.py`).
- Built the shared chart card and wrote the rules for text on screen (`common.py`, [docs/interfaces.md](docs/interfaces.md)).
- Built G4 (energy budget Sankey), G5 (experiment treemap, icicle and sunburst) and G6 (payload × speed heatmap with the Random Forest views).
- Built the Overview landing page with its links to the sections, and moved the Flight & Temporal cards onto the shared card.
- Wrote the architecture test and the smoke test that opens every section.
- Deployed the app on Streamlit Community Cloud and checked it with the real data.
- Kept the decision log ([docs/decisions.md](docs/decisions.md)), reviewed pull requests and set the merge order.

Process rules: [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

Code: MIT (see [LICENSE](LICENSE)). Data: CC BY 4.0, © the original authors.
