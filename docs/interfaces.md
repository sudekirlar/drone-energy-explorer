# Interfaces

How the pieces of the dashboard plug into each other. Read this before writing a chart, a section
or a model. The data contract itself (tables, columns, types, units) is `src/data/schema.py`.

Schema version: see `SCHEMA_VERSION` in `src/data/schema.py`.

---

## 1. Data files

| Table | File (in `data/processed/`, falls back to `data/sample/`) | Produced by | Task |
|---|---|---|---|
| `flights` | `flights.parquet` | Data (+ 3 phase columns from Platform) | T2, T6 |
| `telemetry_1hz` | `telemetry_1hz.parquet` | Data (+ phase columns from Platform) | T2, T6 |
| `phase_energy` | `phase_energy.parquet` | Platform | T6 |
| `waypoints` | `waypoints.parquet` | Platform | T6 |
| `ml_payload` | `ml_payload.parquet` | UI & ML | C1 |
| `quality_log` | `quality_log.json` (list of records) | Data | T2 |
| (metrics) | `ml_metrics.json` | UI & ML | C1 |

Join tables on `flight`. Group-by attributes (payload, speed, altitude, route) live only in
`flights`; other tables do not repeat them.

Columns produced by two roles: `preprocess.py` writes the Data columns; `phases.py` adds the
Platform columns (`flights.cruise_power_w`, `climb_power_w`, `wp_turn_count`;
`telemetry_1hz.t_since_takeoff_s`, `phase`, `sub_phase`). Until `phases.py` exists, sample tables
contain placeholder values for these columns so charts can be built.

### `ml_metrics.json`

Written once by `src/ml/regressor.py`; read with `loader.load_ml_metrics()` (returns `{}` until
the file exists, so cards can show a placeholder). Numbers are never typed into the UI by hand.

```json
{
  "target": "cruise_power_w",
  "features": ["payload_g", "speed_mps", "altitude_m"],
  "n_flights": 181,
  "cv": {"folds": 5, "seeds": 5},
  "random_forest": {"r2_mean": 0.81, "r2_std": 0.01, "mae_mean_w": 14.0, "mae_std_w": 0.5},
  "linear":        {"r2_mean": 0.78, "r2_std": 0.01, "mae_mean_w": 15.0, "mae_std_w": 0.5},
  "grouped_cv":    {"random_forest_r2": 0.79, "linear_r2": 0.76},
  "permutation_importance": {"payload_g": 1.6, "speed_mps": 0.14, "altitude_m": 0.07}
}
```

The values above are only an illustration of the structure (prototype numbers from the chart
guide). UI & ML may extend this structure; changing or removing a key is a contract change.

---

## 2. Reading data (UI layer only)

`src/data/loader.py` has no Streamlit, so caching happens in `app.py`:

```python
# app.py
import streamlit as st
from src.data import loader


@st.cache_data
def get_table(name: str) -> pd.DataFrame:
    return loader.load_table(name)


@st.cache_data
def get_ml_metrics() -> dict:
    return loader.load_ml_metrics()
```

`loader.table_source(name)` returns `"processed"`, `"sample"` or `None`. Show a small "sample data"
badge while any table still comes from `data/sample/`.

A `SchemaError` means a table broke the contract. Fix the producer, not the chart.

---

## 3. Charts (`src/charts/<chart>.py`)

One file per chart, one public function, no Streamlit:

```python
import pandas as pd
import plotly.graph_objects as go

from src import theme


def build_sankey(
    phase_energy: pd.DataFrame, flights: pd.DataFrame, group_by: str, as_percent: bool = False
) -> go.Figure:
    """Energy budget: group -> main phase -> sub-phase."""
    ...
    return fig
```

- Input: tables (already filtered by the sidebar) and the card's control values.
- Output: a `go.Figure`. No `st.` calls, no file reading.
- Message title, axis titles with units, legend when > 1 series, hover with units.
- Colours only from `src/theme.py`.
- Keep data shaping in small helper functions in the same file so they can be tested.

## 4. Sections (`src/sections/<section>.py`)

| Section | File | Owner |
|---|---|---|
| Overview & Data Quality | `overview.py` | Data |
| Flight & Temporal Analysis | `flight_temporal.py` | Data |
| Energy & Experimental Conditions | `energy.py` | Platform |
| Multivariate Analysis & ML | `multivariate_ml.py` | UI & ML |

Each file exposes one function that `app.py` calls when the section is selected in the menu:

```python
def render(tables: dict[str, pd.DataFrame]) -> None:
    """tables: every table in schema.TABLES, already filtered by the sidebar."""
```

The exact filter object and how `app.py` builds `tables` are defined by UI & ML in T4; sections
only rely on receiving the filtered tables.

### Card pattern

Every chart is shown in the shared card from `src/sections/common.py`, so all cards look and
read the same. A card has fixed parts, always in this order:

| Part | What it says |
|---|---|
| Title | The chart's main message, as one sentence (Guideline #7). Not a question, no task codes (no "G1"). |
| How to read | One sentence: what the marks, axes and colours mean. |
| Data | One sentence: which flights the chart uses, and why. |
| Controls | The card's own widgets. |
| Chart | The Plotly figure, drawn with `card.plot`. |
| Finding | What the real data shows, with numbers. Computed from the filtered data when the claim depends on the filters. |
| About this chart (folded) | Why this chart · What you see (encodings) · What you can do (Yi et al. interaction types) · From the lectures · Made by (full name). |

The texts live in one `CardInfo` per chart, next to the card function:

```python
from src.sections.common import CardInfo, chart_card

SANKEY = CardInfo(
    title="At 100 m, take-off and landing use half of the energy.",
    how_to_read="Bands flow from flight groups to phases; a wider band means more energy (Wh).",
    data="The 181 R1 design flights; the route grouping adds R2-R7.",
    finding="...",
    why="Energy is a budget: the phases of a flight add up to its total, as in a Sankey.",
    encoding="Band width shows energy. Colour shows the phase, as in every other chart.",
    interaction="Change the grouping (reconfigure) and switch to percentages (encode).",
    lecture="Lecture 6 (trees and flows): flow diagrams show how a total divides.",
    author="Sude Kırlar",
)


@st.fragment
def sankey_card(tables: dict[str, pd.DataFrame]) -> None:
    with chart_card(SANKEY) as card:
        group_by = st.selectbox(
            "Group by", ["altitude", "speed", "payload", "route"], key="sankey_group_by"
        )
        card.plot(
            build_sankey(tables["phase_energy"], tables["flights"], group_by), key="sankey_chart"
        )
        card.finding = "..."  # optional: replaces SANKEY.finding with numbers from the data
```

Each card function is an `@st.fragment`, so its own controls rerun only that card.

### Writing on screen

Everything a visitor reads is in simple English, in short, full sentences.

- One idea per sentence. Present tense: "Power rises", not "Power will rise".
- Say what the visitor sees, not how we built it. No internal words: "Platform", "contract",
  "schema", task codes. Say "estimated phase", never just "phase label".
- Give units in brackets the first time: "power (W)", "speed (m/s)".
- Numbers in findings come from the real data. A number that depends on the filters is computed;
  a fixed number is checked against the processed tables in the Saturday consistency pass (Q1).
- Write "waypoint" in full in sentences; "WP1" is fine as a label on the chart.
- Name people, not roles: "Made by İlayda Demir", not "Author: Data role".

**Widget keys** are unique and start with the chart scope (`sankey_`, `stc_`, `pcp_`, ...).

---

## 5. Shared state between charts (`st.session_state`)

Only these keys are shared across cards. Add a key here (PR) before using it in two places.

| Key | Type | Written by | Read by | Default |
|---|---|---|---|---|
| `menu_section` | `str` | top menu (`app.py`) | `app.py` | `"Overview"` |
| `map_flights` | `list[int]` | route map (G1) | Space-Time Cube, timeline (E2) | `[]` |
| `cube_flights` | `list[int]` | Space-Time Cube (G2) / "Send to 3D" | Space-Time Cube | `[278, 8, 77]` |
| `timeline_flight` | `int` | timeline (G3) / "Open in timeline" | timeline | `77` |
| `kmeans_k` | `int` | PCP k slider (G7) | SPLOM (G8), flight × time heatmap (G10) | `3` |

A button that changes another card's key calls `st.rerun()` after setting it.

K-means labels are not stored in session state: every card calls the same cached function
(`run_kmeans(flights, k)` from `src/ml/clustering.py`, cached in the UI layer) with `kmeans_k`, so
the same flights always get the same cluster.

---

## 6. Changing the contract

1. Edit `src/data/schema.py` (and this file if a key or file changes).
2. Bump `SCHEMA_VERSION` (new column: minor; renamed or removed column: major).
3. PR with the `contract` label, approved by Platform and by the role that produces the table.
4. Producers update their output; the test `test_repo_tables_follow_the_contract` checks the
   files in `data/sample/` and `data/processed/` against the new contract.
