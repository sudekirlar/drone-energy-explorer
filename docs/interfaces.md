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
  "cv_folds": 5,
  "cv_seeds": [0, 1, 2, 3, 4],
  "random_forest": {
    "cv": {"r2_mean": 0.788, "r2_std": 0.008, "mae_mean": 14.91, "mae_std": 0.33},
    "grouped_cv": {"r2": 0.760, "mae": 15.42, "n_groups": 60}
  },
  "linear_regression": {
    "cv": {"r2_mean": 0.772, "r2_std": 0.001, "mae_mean": 15.42, "mae_std": 0.03},
    "grouped_cv": {"r2": 0.746, "mae": 16.08, "n_groups": 60}
  },
  "permutation_importance": [
    {"feature": "payload_g", "importance_mean": 1.587, "importance_std": 0.129},
    {"feature": "speed_mps", "importance_mean": 0.058, "importance_std": 0.036},
    {"feature": "altitude_m", "importance_mean": 0.014, "importance_std": 0.014}
  ]
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
| Title | The chart's short name, a few words: "Flight routes", "Energy budget". No task codes. |
| How to read | One or two full sentences: what the marks, axes and colours mean. |
| Controls | The card's own widgets. |
| Chart | The Plotly figure, drawn with `card.plot`. Every colour used for a category has a legend. |
| Finding (optional) | One or two sentences about what is on screen now, computed from the filtered data and the card's controls. Left out when nothing useful can be computed. Never a fixed sentence about flights the visitor may not be looking at. |
| About this chart (folded) | Short paragraphs: why the chart is useful for this data, how it encodes the data, what the visitor can do, which flights it uses, and who made it. |

The fixed texts live in one `CardInfo` per chart, next to the card function:

```python
from src.sections.common import CardInfo, chart_card

SANKEY = CardInfo(
    title="Energy budget",
    how_to_read=(
        "Bands flow from groups of flights to flight phases. A wider band means more energy."
    ),
    about=(
        "A flight's energy is shared between its phases, and the parts add up to the total. "
        "A Sankey diagram shows exactly this kind of budget.",
        "...",
    ),
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
        card.finding = describe_sankey(tables["phase_energy"], tables["flights"], group_by)
```

Each card function is an `@st.fragment`, so its own controls rerun only that card.

### Writing on screen

Everything a visitor reads is in simple English, in short, full sentences.

- Write whole sentences with a subject and a verb. No clipped fragments such as
  "Why this chart." or "A map loses two dimensions: time and altitude".
- One idea per sentence. Present tense: "Power rises", not "Power will rise".
- Say what the visitor sees, not how we built it. No internal words: "Platform", "contract",
  "schema", task codes. Say "estimated phase", never just "phase label".
- Give units in brackets the first time: "power (W)", "speed (m/s)".
- A finding talks only about what is on screen, and its numbers are computed from the data.
- Write "waypoint" in full in sentences; "WP1" is fine as a label on the chart.
- Write for the visitor, not for the grader. No lecture numbers, slide references or course
  vocabulary on screen ("Lecture 7", "Yi et al.", "encode"); those belong in the report, the
  README and the presentation (`docs/decisions.md` keeps the reasons for each chart).
- Name people, not roles: "This chart was made by İlayda Demir."

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
