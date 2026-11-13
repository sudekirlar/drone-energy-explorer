"""Smoke test: the app opens and every section renders without an exception.

The tables are built in memory from ``src/data/schema.py`` and handed to the app by replacing
the loader's reading functions for the duration of the test. Nothing is written to disk, the
test does not depend on ``data/sample/`` or ``data/processed/``, and the fake tables follow the
contract automatically when it changes.

The test only answers "does it open?". It does not check that a chart is correct.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from src.data import loader, schema

APP = Path(__file__).resolve().parents[1] / "app.py"
SECTIONS = ["Overview", "Flight & Temporal", "Energy & Conditions", "Multivariate & ML"]
SECONDS_PER_FLIGHT = 16  # two rows for each of the eight sub-phases
WAYPOINTS_PER_FLIGHT = 3  # home + two turns


# ---- fake tables built from the contract -------------------------------------------------------


def _default_values(col: schema.Column, n: int) -> list:
    """Valid placeholder values for one column, chosen only from its type and allowed values."""
    if col.allowed is not None:
        return [col.allowed[i % len(col.allowed)] for i in range(n)]
    if col.dtype == schema.INT:
        return list(range(1, n + 1))
    if col.dtype == schema.FLOAT:
        return [float(i + 1) for i in range(n)]
    if col.dtype == schema.BOOL:
        return [False] * n
    if col.dtype == schema.DATETIME:
        return list(pd.date_range("2019-04-01 10:00", periods=n, freq="h"))
    return [f"{col.name}_{i}" for i in range(n)]


def _fake_table(table: schema.Table, n: int, **overrides: list) -> pd.DataFrame:
    """Every contract column gets a placeholder; ``overrides`` set the columns that matter."""
    data = {col.name: _default_values(col, n) for col in table.columns}
    unknown = set(overrides) - set(data)
    assert not unknown, f"{table.name} has no columns {sorted(unknown)}"
    data.update(overrides)
    return pd.DataFrame(data)


def _fake_tables() -> dict[str, pd.DataFrame]:
    # Six R1 flights covering the three payloads, and one R7 flight without a target altitude.
    flight_ids = [1, 2, 3, 4, 5, 6, 278]
    routes = ["R1"] * 6 + ["R7"]
    n = len(flight_ids)
    flights = _fake_table(
        schema.FLIGHTS,
        n,
        flight=flight_ids,
        route=routes,
        payload_g=[0, 250, 500, 0, 250, 500, 0],
        speed_mps=[4, 8, 12, 4, 8, 12, 6],
        altitude_m=[25.0, 50.0, 100.0, 25.0, 50.0, 100.0, np.nan],
        variable_altitude=[r == "R7" for r in routes],
        in_design=[r == "R1" for r in routes],
        is_outlier=[False, False, False, False, False, True, False],
        outlier_reason=[None] * 5 + ["Joint deviation in energy, duration and mean power", None],
        energy_wh=[18.0, 21.0, 24.0, 19.0, 22.0, 25.0, 23.0],
        wh_per_km=[45.0, 40.0, 42.0, 46.0, 41.0, 43.0, 44.0],
    )

    # telemetry_1hz: every flight passes through every sub-phase, in order.
    sub_phases = [s for s in schema.SUB_PHASES for _ in range(SECONDS_PER_FLIGHT // 8)]
    m = n * SECONDS_PER_FLIGHT
    telemetry = _fake_table(
        schema.TELEMETRY,
        m,
        flight=[f for f in flight_ids for _ in range(SECONDS_PER_FLIGHT)],
        t_s=[float(t) for _ in flight_ids for t in range(SECONDS_PER_FLIGHT)],
        t_since_takeoff_s=[float(t - 2) for _ in flight_ids for t in range(SECONDS_PER_FLIGHT)],
        sub_phase=sub_phases * n,
        phase=[schema.SUB_PHASE_PARENT[s] for s in sub_phases] * n,
    )

    # phase_energy: one row per flight and sub-phase.
    k = len(schema.SUB_PHASES)
    phase_energy = _fake_table(
        schema.PHASE_ENERGY,
        n * k,
        flight=[f for f in flight_ids for _ in range(k)],
        sub_phase=list(schema.SUB_PHASES) * n,
        phase=[schema.SUB_PHASE_PARENT[s] for s in schema.SUB_PHASES] * n,
    )

    w = WAYPOINTS_PER_FLIGHT
    waypoints = _fake_table(
        schema.WAYPOINTS,
        n * w,
        flight=[f for f in flight_ids for _ in range(w)],
        wp_index=list(range(w)) * n,
        turn_angle_deg=[np.nan, 140.0, 135.0] * n,
    )

    r1_flights = [f for f, r in zip(flight_ids, routes, strict=True) if r == "R1"]
    ml_payload = _fake_table(schema.ML_PAYLOAD, len(r1_flights), flight=r1_flights)

    quality_log = _fake_table(schema.QUALITY_LOG, 3)

    return {
        "flights": flights,
        "telemetry_1hz": telemetry,
        "phase_energy": phase_energy,
        "waypoints": waypoints,
        "ml_payload": ml_payload,
        "quality_log": quality_log,
    }


@pytest.fixture
def fake_data(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, pd.DataFrame]]:
    """Serve the fake tables to the app through the loader, without touching the disk."""
    # Validating here first means a broken fake table fails as a test setup error,
    # not as a confusing error inside the app.
    tables = {name: loader.validate(df, schema.TABLES[name]) for name, df in _fake_tables().items()}
    assert set(tables) == set(schema.TABLES), "fake tables must cover every contract table"

    monkeypatch.setattr(loader, "table_source", lambda name, data_dir=None: "sample")
    monkeypatch.setattr(loader, "load_table", lambda name, data_dir=None: tables[name].copy())
    monkeypatch.setattr(loader, "load_ml_metrics", lambda data_dir=None: {})

    # app.py caches tables with st.cache_data; clear it so no other test's data leaks in.
    st.cache_data.clear()
    yield tables
    st.cache_data.clear()


# ---- helpers ------------------------------------------------------------------------------------


def _problems(at: AppTest) -> str:
    """Readable summary of everything that went wrong on the page (empty string if nothing)."""
    lines = [f"exception: {e.message}\n" + "\n".join(e.stack_trace) for e in at.exception]
    lines += [f"st.error: {e.value}" for e in at.error]
    return "\n\n".join(lines)


def _open_app(section: str | None = None) -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=30)
    if section is not None:
        # app.py reads this key to choose the section, so only this section runs.
        at.session_state["menu_section"] = section
    return at.run()


# ---- tests --------------------------------------------------------------------------------------


def test_menu_lists_the_four_sections(fake_data: dict[str, pd.DataFrame]) -> None:
    at = _open_app()
    # The menu is drawn only after data loading and filtering succeed, so its absence means
    # the app stopped early (for example on a contract error or "no flights").
    assert len(at.segmented_control) == 1, "menu not shown:\n" + _problems(at)
    assert at.segmented_control[0].options == SECTIONS


@pytest.mark.parametrize("section", SECTIONS)
def test_section_renders_without_error(fake_data: dict[str, pd.DataFrame], section: str) -> None:
    at = _open_app(section)
    assert len(at.segmented_control) == 1, "menu not shown:\n" + _problems(at)
    assert at.segmented_control[0].value == section
    # Compare a plain string, so pytest prints only our summary and not the whole page tree.
    problems = _problems(at)
    assert not problems, f"'{section}' failed:\n{problems}"
