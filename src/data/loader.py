"""The single way the app reads data: find the file, read it, check it against the contract.

For every table the loader looks in ``data/processed/`` first (real tables from preprocessing).
If the file is not there yet it falls back to ``data/sample/`` (small tables that follow the same
contract). Nobody has to change chart code when the real data arrives.

Every table is validated against ``src/data/schema.py``. A missing column, a wrong type, a missing
value in a required column or an unknown category stops loading with a message that names the
table and the column. Columns that are not in the contract are dropped, so nothing in the app can
depend on them by accident.

Caching is done in the UI layer, not here (this module must not import Streamlit):

    # app.py
    @st.cache_data
    def get_table(name: str) -> pd.DataFrame:
        return loader.load_table(name)
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from pandas.api import types as ptypes

from src.data import schema
from src.data.schema import BOOL, DATETIME, FLOAT, INT, STR, Table

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
SOURCES = ("processed", "sample")  # search order
ML_METRICS_FILE = "ml_metrics.json"


class SchemaError(ValueError):
    """A table does not follow the data contract."""


# ---- finding files ------------------------------------------------------------------------------


def find_table_file(name: str, data_dir: Path = DATA_DIR) -> Path:
    """Path of a table, from data/processed if present, otherwise data/sample."""
    table = _table(name)
    for source in SOURCES:
        path = data_dir / source / table.filename
        if path.exists():
            return path
    searched = ", ".join(f"data/{s}/{table.filename}" for s in SOURCES)
    raise FileNotFoundError(f"Table '{name}' not found. Looked for: {searched}")


def table_source(name: str, data_dir: Path = DATA_DIR) -> str | None:
    """'processed', 'sample' or None: where the table currently comes from (for a status badge)."""
    try:
        return find_table_file(name, data_dir).parent.name
    except FileNotFoundError:
        return None


# ---- validation ---------------------------------------------------------------------------------

_DTYPE_CHECK = {
    INT: ptypes.is_integer_dtype,
    FLOAT: ptypes.is_numeric_dtype,  # ints are accepted where floats are expected
    STR: lambda s: ptypes.is_string_dtype(s) or ptypes.is_object_dtype(s),
    BOOL: ptypes.is_bool_dtype,
    DATETIME: ptypes.is_datetime64_any_dtype,
}


def validate(df: pd.DataFrame, table: Table) -> pd.DataFrame:
    """Check a DataFrame against the contract and return it with exactly the contract columns.

    Raises SchemaError listing every problem found, not only the first one.
    """
    problems: list[str] = []

    missing = [c for c in table.column_names if c not in df.columns]
    if missing:
        problems.append(f"missing columns: {missing}")

    for col in table.columns:
        if col.name not in df.columns:
            continue
        series = df[col.name]
        if not col.nullable and series.isna().any():
            problems.append(f"'{col.name}' has {int(series.isna().sum())} missing values")
        non_null = series.dropna()
        if len(non_null) and not _DTYPE_CHECK[col.dtype](series):
            problems.append(f"'{col.name}' should be {col.dtype}, found {series.dtype}")
        if col.allowed is not None:
            unknown = sorted(set(non_null.astype(str)) - set(col.allowed))
            if unknown:
                problems.append(f"'{col.name}' has values outside {list(col.allowed)}: {unknown}")

    present_key = [k for k in table.key if k in df.columns]
    if len(present_key) == len(table.key) and df.duplicated(list(table.key)).any():
        problems.append(f"duplicate rows for key {list(table.key)}")

    if problems:
        details = "\n  - ".join(problems)
        raise SchemaError(
            f"Table '{table.name}' does not follow schema v{schema.SCHEMA_VERSION}:\n  - {details}"
        )
    return df[table.column_names].reset_index(drop=True)


# ---- loading ------------------------------------------------------------------------------------


def load_table(name: str, data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Read a table (processed, else sample) and validate it against the contract."""
    table = _table(name)
    path = find_table_file(name, data_dir)
    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
    elif path.suffix == ".json":
        df = pd.DataFrame(json.loads(path.read_text(encoding="utf-8")))
    else:
        raise ValueError(f"Unsupported file type for '{name}': {path.name}")
    try:
        return validate(df, table)
    except SchemaError as err:
        raise SchemaError(f"{err}\n  (file: {path.relative_to(data_dir.parent)})") from None


def load_flights(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    return load_table("flights", data_dir)


def load_telemetry(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    return load_table("telemetry_1hz", data_dir)


def load_phase_energy(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    return load_table("phase_energy", data_dir)


def load_waypoints(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    return load_table("waypoints", data_dir)


def load_ml_payload(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    return load_table("ml_payload", data_dir)


def load_quality_log(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    return load_table("quality_log", data_dir)


def load_ml_metrics(data_dir: Path = DATA_DIR) -> dict:
    """Model metrics written by src/ml/regressor.py (structure in docs/interfaces.md).

    Returns an empty dict while the file does not exist yet, so cards can show a placeholder.
    """
    for source in SOURCES:
        path = data_dir / source / ML_METRICS_FILE
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _table(name: str) -> Table:
    try:
        return schema.TABLES[name]
    except KeyError:
        raise KeyError(f"Unknown table '{name}'. Known: {list(schema.TABLES)}") from None
