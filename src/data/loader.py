"""Data adapter for the Streamlit dashboard."""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def load_flights() -> pd.DataFrame:
    """Load processed team data, or demo data if unavailable."""
    candidates = [
        ROOT / "data" / "flight_summary.csv",
        ROOT / "data" / "flights_summary.csv",
        ROOT / "data" / "flight_level.csv",
        ROOT / "data" / "processed_flights.csv",
        ROOT / "data" / "flights.csv",
        ROOT / "flight_summary.csv",
    ]

    for path in candidates:
        if path.exists():
            df = pd.read_csv(path)
            if not df.empty:
                return df

    from src.data.demo import make_demo_data
    return make_demo_data()
