"""Tests for the data contract (schema.py) and the loading layer (loader.py)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import pytest

from src.data import loader, schema
from src.data.schema import BOOL, DATETIME, FLOAT, INT, STR, Table

ROOT = Path(__file__).resolve().parents[1]


def example_frame(table: Table, n: int = 3) -> pd.DataFrame:
    """A small DataFrame that follows the contract, for tests only."""
    data = {}
    for col in table.columns:
        if col.allowed is not None:
            values = [col.allowed[i % len(col.allowed)] for i in range(n)]
        elif col.dtype == INT:
            values = list(range(1, n + 1))
        elif col.dtype == FLOAT:
            values = [float(i) + 0.5 for i in range(n)]
        elif col.dtype == STR:
            values = [f"{col.name}-{i}" for i in range(n)]
        elif col.dtype == BOOL:
            values = [i % 2 == 0 for i in range(n)]
        elif col.dtype == DATETIME:
            values = list(pd.date_range("2019-04-07 10:00", periods=n, freq="h"))
        else:
            raise AssertionError(col.dtype)
        data[col.name] = values
    return pd.DataFrame(data)


def write_table(data_dir: Path, source: str, table: Table, df: pd.DataFrame) -> Path:
    path = data_dir / source / table.filename
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".json":
        path.write_text(df.to_json(orient="records"), encoding="utf-8")
    else:
        df.to_parquet(path, index=False)
    return path


# ---- the contract itself ------------------------------------------------------------------------


@pytest.mark.parametrize("table", schema.TABLES.values(), ids=list(schema.TABLES))
def test_column_names_are_lowercase_and_unique(table: Table) -> None:
    names = table.column_names
    assert len(names) == len(set(names)), f"duplicate column in {table.name}"
    for name in names:
        assert re.fullmatch(r"[a-z][a-z0-9_]*", name), f"{table.name}.{name} is not lowercase"


@pytest.mark.parametrize("table", schema.TABLES.values(), ids=list(schema.TABLES))
def test_keys_and_producers_are_valid(table: Table) -> None:
    for key in table.key:
        assert key in table.column_names
        assert not table.column(key).nullable
    for col in table.columns:
        assert col.producer in schema.PRODUCER_LABEL
        assert col.dtype in (INT, FLOAT, STR, BOOL, DATETIME)


def test_every_sub_phase_has_a_parent_phase() -> None:
    assert set(schema.SUB_PHASE_PARENT) == set(schema.SUB_PHASES)
    assert set(schema.SUB_PHASE_PARENT.values()) <= set(schema.PHASES)


def test_data_dictionary_has_one_row_per_column() -> None:
    expected = sum(len(t.columns) for t in schema.TABLES.values())
    assert len(schema.data_dictionary()) == expected


# ---- validation ---------------------------------------------------------------------------------


@pytest.mark.parametrize("table", schema.TABLES.values(), ids=list(schema.TABLES))
def test_valid_frame_passes_and_keeps_contract_order(table: Table) -> None:
    df = example_frame(table)
    df["not_in_contract"] = 1
    out = loader.validate(df[list(reversed(df.columns))], table)
    assert list(out.columns) == table.column_names


def test_missing_column_is_reported_by_name() -> None:
    df = example_frame(schema.FLIGHTS).drop(columns=["wh_per_km"])
    with pytest.raises(loader.SchemaError, match="wh_per_km"):
        loader.validate(df, schema.FLIGHTS)


def test_wrong_type_is_reported() -> None:
    df = example_frame(schema.FLIGHTS)
    df["payload_g"] = df["payload_g"].astype(str)
    with pytest.raises(loader.SchemaError, match="payload_g.*should be int"):
        loader.validate(df, schema.FLIGHTS)


def test_missing_value_in_required_column_is_reported() -> None:
    df = example_frame(schema.FLIGHTS)
    df.loc[0, "energy_wh"] = None
    with pytest.raises(loader.SchemaError, match="energy_wh.*missing"):
        loader.validate(df, schema.FLIGHTS)


def test_missing_value_in_nullable_column_is_accepted() -> None:
    df = example_frame(schema.FLIGHTS)
    df.loc[0, "altitude_m"] = None  # R7 has no single target altitude
    loader.validate(df, schema.FLIGHTS)


def test_unknown_phase_is_reported() -> None:
    df = example_frame(schema.PHASE_ENERGY)
    df.loc[0, "sub_phase"] = "Hover"
    with pytest.raises(loader.SchemaError, match="Hover"):
        loader.validate(df, schema.PHASE_ENERGY)


def test_duplicate_key_is_reported() -> None:
    df = example_frame(schema.FLIGHTS)
    df.loc[1, "flight"] = df.loc[0, "flight"]
    with pytest.raises(loader.SchemaError, match="duplicate"):
        loader.validate(df, schema.FLIGHTS)


# ---- loading ------------------------------------------------------------------------------------


def test_processed_is_preferred_over_sample(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    sample = example_frame(schema.FLIGHTS, n=2)
    processed = example_frame(schema.FLIGHTS, n=4)
    write_table(data_dir, "sample", schema.FLIGHTS, sample)
    assert loader.table_source("flights", data_dir) == "sample"
    assert len(loader.load_flights(data_dir)) == 2

    write_table(data_dir, "processed", schema.FLIGHTS, processed)
    assert loader.table_source("flights", data_dir) == "processed"
    assert len(loader.load_flights(data_dir)) == 4


def test_missing_table_gives_a_clear_message(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="data/processed/waypoints.parquet"):
        loader.load_waypoints(tmp_path / "data")
    assert loader.table_source("waypoints", tmp_path / "data") is None


def test_json_table_is_loaded(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    write_table(data_dir, "sample", schema.QUALITY_LOG, example_frame(schema.QUALITY_LOG))
    assert len(loader.load_quality_log(data_dir)) == 3


def test_ml_metrics_is_empty_until_written(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    assert loader.load_ml_metrics(data_dir) == {}
    (data_dir / "processed").mkdir(parents=True)
    (data_dir / "processed" / "ml_metrics.json").write_text(json.dumps({"n_flights": 181}))
    assert loader.load_ml_metrics(data_dir)["n_flights"] == 181


def test_unknown_table_name_is_rejected() -> None:
    with pytest.raises(KeyError, match="Unknown table"):
        loader.load_table("flight")


# ---- the real files in the repo -----------------------------------------------------------------


@pytest.mark.parametrize("name", list(schema.TABLES))
@pytest.mark.parametrize("source", loader.SOURCES)
def test_repo_tables_follow_the_contract(name: str, source: str) -> None:
    """Runs on data/sample and data/processed once those files exist (T5, T2, T6, C1)."""
    path = ROOT / "data" / source / schema.TABLES[name].filename
    if not path.exists():
        pytest.skip(f"{path.relative_to(ROOT)} not created yet")
    loader.validate(
        pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_json(path),
        schema.TABLES[name],
    )
