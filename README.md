# Drone Delivery Energy Explorer

**Live app:** https://data-energy-explorer.streamlit.app/

CEN445 Introduction to Data Visualization · Çukurova University · Fall 2026
Team: Sude Kırlar, İlayda Demir, Pelin Gül Kızılkılıç

> How do payload, cruise speed and altitude shape the energy a delivery drone spends,
> and where in the flight does that energy go?

An interactive Streamlit dashboard built on 209 real test flights of a DJI Matrice 100 package-delivery
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

TODO: table of the ten charts (chart, sub-question, interaction, author).

## Data cleaning

TODO: summary of the cleaning rules and their effect (details in the app's Data Quality section).

## Machine learning

TODO: K-means clustering and Random Forest regression, evaluation and limitations.

## Contributions

TODO: who did what. Process rules: [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

Code: MIT (see [LICENSE](LICENSE)). Data: CC BY 4.0, © the original authors.
