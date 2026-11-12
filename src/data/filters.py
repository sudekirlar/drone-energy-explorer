"""Immutable FilterState and shared apply_filters() logic."""

from dataclasses import dataclass

import pandas as pd


def _resolve_column(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


@dataclass(frozen=True)
class FilterState:
    payloads: tuple = ()
    altitudes: tuple = ()
    speeds: tuple = ()
    hide_flagged: bool = False
    include_other_routes: bool = True

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> "FilterState":
        payload_col = _resolve_column(df, ("payload_g", "payload"))
        alt_col = _resolve_column(df, ("target_altitude", "altitude"))
        speed_col = _resolve_column(df, ("target_speed", "speed"))

        payload_opts = (
            tuple(sorted(df[payload_col].dropna().unique().tolist())) if payload_col else ()
        )
        alt_opts = tuple(sorted(df[alt_col].dropna().unique().tolist())) if alt_col else ()
        speed_opts = tuple(sorted(df[speed_col].dropna().unique().tolist())) if speed_col else ()

        return cls(
            payloads=payload_opts,
            altitudes=alt_opts,
            speeds=speed_opts,
            hide_flagged=False,
            include_other_routes=True,
        )

    @property
    def payload_options(self) -> list:
        return list(self.payloads)

    @property
    def altitude_options(self) -> list:
        return list(self.altitudes)

    @property
    def speed_options(self) -> list:
        return list(self.speeds)


def apply_filters(df: pd.DataFrame, filters: FilterState) -> pd.DataFrame:
    """Filter the dataframe using FilterState with column alias support."""
    filtered = df.copy()

    payload_col = _resolve_column(filtered, ("payload_g", "payload"))
    if payload_col and filters.payloads:
        filtered = filtered[filtered[payload_col].isin(filters.payloads)]

    alt_col = _resolve_column(filtered, ("target_altitude", "altitude"))
    if alt_col and filters.altitudes:
        filtered = filtered[filtered[alt_col].isin(filters.altitudes)]

    speed_col = _resolve_column(filtered, ("target_speed", "speed"))
    if speed_col and filters.speeds:
        filtered = filtered[filtered[speed_col].isin(filters.speeds)]

    if filters.hide_flagged and "flagged" in filtered.columns:
        filtered = filtered[~filtered["flagged"].astype(bool)]

    if not filters.include_other_routes and "route" in filtered.columns:
        other_routes = {"R2", "R3", "R4", "R5", "R6", "R7"}
        filtered = filtered[~filtered["route"].astype(str).isin(other_routes)]

    return filtered
