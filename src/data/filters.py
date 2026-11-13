"""Immutable FilterState and shared filtering across all contract tables."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class FilterState:
    payloads: tuple[int, ...] = ()
    altitudes: tuple[float, ...] = ()
    speeds: tuple[int, ...] = ()
    include_missing_altitude: bool = True
    hide_outliers: bool = False
    include_other_routes: bool = False

    @classmethod
    def from_flights(cls, flights: pd.DataFrame) -> FilterState:
        payload_opts = tuple(sorted(int(x) for x in flights["payload_g"].dropna().unique()))
        alt_opts = tuple(sorted(float(x) for x in flights["altitude_m"].dropna().unique()))
        speed_opts = tuple(sorted(int(x) for x in flights["speed_mps"].dropna().unique()))
        return cls(
            payloads=payload_opts,
            altitudes=alt_opts,
            speeds=speed_opts,
            include_missing_altitude=True,
            hide_outliers=False,
            include_other_routes=False,
        )

    @property
    def payload_options(self) -> list[int]:
        return list(self.payloads)

    @property
    def altitude_options(self) -> list[float]:
        return list(self.altitudes)

    @property
    def speed_options(self) -> list[int]:
        return list(self.speeds)


def filter_flights(flights: pd.DataFrame, state: FilterState) -> pd.DataFrame:
    """Filter the flights table using exact contract column names."""
    mask = pd.Series(True, index=flights.index)

    if state.payloads:
        mask &= flights["payload_g"].isin(state.payloads)
    else:
        mask &= False

    if state.altitudes:
        alt_match = flights["altitude_m"].isin(state.altitudes)
        if state.include_missing_altitude:
            alt_match |= flights["altitude_m"].isna()
        mask &= alt_match
    elif state.include_missing_altitude:
        mask &= flights["altitude_m"].isna()
    else:
        mask &= False

    if state.speeds:
        mask &= flights["speed_mps"].isin(state.speeds)
    else:
        mask &= False

    if state.hide_outliers:
        mask &= ~flights["is_outlier"].astype(bool)

    if not state.include_other_routes:
        # The experiment: R1 with payload 0/250/500 g. Flight 76 (750 g) is R1 but not in it.
        mask &= flights["in_design"].astype(bool)

    return flights.loc[mask].reset_index(drop=True)


def apply_filters(tables: dict[str, pd.DataFrame], state: FilterState) -> dict[str, pd.DataFrame]:
    """Filter flights and keep matching flight rows across all loaded tables."""
    filtered_flights = filter_flights(tables["flights"], state)
    valid_flights = set(filtered_flights["flight"].tolist())

    result: dict[str, pd.DataFrame] = {"flights": filtered_flights}
    for name, df in tables.items():
        if name == "flights":
            continue
        if "flight" in df.columns:
            result[name] = df[df["flight"].isin(valid_flights)].reset_index(drop=True)
        else:
            result[name] = df.copy()
    return result
