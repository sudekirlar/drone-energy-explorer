"""Contract/sample quality tests for Data-owned T5 examples."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.data import loader, schema
from src.data.build_samples import choose_flights, validate_energy

ROOT = Path(__file__).resolve().parents[1]


def test_flight_selection_spans_routes_and_levels() -> None:
    rows = []
    for i in range(1, 61):
        rows.append(
            {
                "flight": i,
                "route": "R1",
                "in_design": True,
                "payload_g": [0, 250, 500][i % 3],
                "speed_mps": [4, 6, 8, 10, 12][i % 5],
                "altitude_m": [25.0, 50.0, 75.0, 100.0][i % 4],
            }
        )
    rows.extend(
        [
            {
                "flight": 200,
                "route": "R6",
                "in_design": False,
                "payload_g": 0,
                "speed_mps": 4,
                "altitude_m": 25.0,
            },
            {
                "flight": 201,
                "route": "R7",
                "in_design": False,
                "payload_g": 0,
                "speed_mps": 4,
                "altitude_m": float("nan"),
            },
        ]
    )
    selected = choose_flights(pd.DataFrame(rows))
    assert len(selected) == 17
    assert 200 in selected and 201 in selected
    assert len(set(selected)) == len(selected)


def test_energy_reconciliation_detects_mismatch() -> None:
    flights = pd.DataFrame({"flight": [1, 2], "energy_wh": [1.0, 2.0]})
    raw = pd.DataFrame(
        {
            "flight": [1, 1, 2, 2],
            "t_s": [0, 1, 0, 1],
            "energy_wh": [0.0, 1.0, 0.0, 2.0],
            "current_a": [1.0] * 4,
            "power_w": [10.0] * 4,
        }
    )
    assert validate_energy(flights, raw) == 0.0
    raw.loc[3, "energy_wh"] = 3.0
    with pytest.raises(ValueError, match="energy conservation"):
        validate_energy(flights, raw)


def test_committed_sample_tables_obey_contract() -> None:
    for name in ("flights", "telemetry_1hz", "quality_log"):
        path = ROOT / "data" / "sample" / schema.TABLES[name].filename
        if not path.exists():
            pytest.skip("T5 samples have not been generated")
        assert not loader.load_table(name).empty


def test_sample_phase_columns_are_obviously_placeholders() -> None:
    path = ROOT / "data" / "sample" / "telemetry_1hz.parquet"
    if not path.exists():
        pytest.skip("T5 samples have not been generated")
    demo = pd.read_parquet(path)
    assert set(demo["phase"]) == {"Ground"}
    assert set(demo["sub_phase"]) == {"Ground"}
    assert (demo["t_since_takeoff_s"] == 0).all()
