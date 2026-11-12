"""Data contract: every table the app reads, with its columns, types and units.

This file is the single agreement between the people who produce tables (preprocessing, phases,
models) and the people who draw charts. Charts and models may rely on exactly these columns.

Rules
- Column names are lowercase with the unit at the end: ``power_w``, ``energy_wh``, ``alt_rel_m``.
- Raw CMU column names (``battery_voltage``, ``wind_speed`` ...) never appear here; only
  ``src/data/preprocess.py`` translates them.
- Changing this file is a contract change: open a PR with the ``contract`` label, get approval
  from Platform and from the role that produces the table, and bump ``SCHEMA_VERSION``.

No Streamlit here (see tests/test_architecture.py).
"""

from __future__ import annotations

from dataclasses import dataclass

SCHEMA_VERSION = "1.0.0"

# Producers (roles), used in the data dictionary and to know whom to ask.
DATA = "data"  # İlayda: preprocess.py
PLATFORM = "platform"  # Sude: phases.py
UIML = "uiml"  # Pelin: ml/

# Allowed values of categorical columns. Labels are already in English for display.
ROUTES = ("R1", "R2", "R3", "R4", "R5", "R6", "R7")
PHASES = ("Ground", "Take-off", "Cruise", "Manoeuvre", "Landing")
SUB_PHASES = (
    "Ground",
    "Spool-up",
    "Climb",
    "Straight leg",
    "Sloped cruise",
    "WP turn",
    "Speed change",
    "Descent",
)
# Which main phase each sub-phase belongs to (chart guide, "Uçuşun evreleri").
SUB_PHASE_PARENT = {
    "Ground": "Ground",
    "Spool-up": "Take-off",
    "Climb": "Take-off",
    "Straight leg": "Cruise",
    "Sloped cruise": "Cruise",
    "WP turn": "Manoeuvre",
    "Speed change": "Manoeuvre",
    "Descent": "Landing",
}
# ISO/IEC 25012 data quality characteristics (inherent first, then system-dependent).
ISO25012 = (
    "Accuracy",
    "Completeness",
    "Consistency",
    "Credibility",
    "Currentness",
    "Accessibility",
    "Compliance",
    "Confidentiality",
    "Efficiency",
    "Precision",
    "Traceability",
    "Understandability",
    "Availability",
    "Portability",
    "Recoverability",
)

INT, FLOAT, STR, BOOL, DATETIME = "int", "float", "str", "bool", "datetime"


@dataclass(frozen=True)
class Column:
    name: str
    dtype: str  # one of INT, FLOAT, STR, BOOL, DATETIME
    unit: str  # "" when the column has no unit
    description: str
    producer: str  # DATA, PLATFORM or UIML
    nullable: bool = False  # may the column contain missing values?
    allowed: tuple[str, ...] | None = None  # allowed values for categorical columns


@dataclass(frozen=True)
class Table:
    name: str
    row: str  # what one row represents
    filename: str  # file name inside data/processed/ and data/sample/
    key: tuple[str, ...]  # columns that identify a row
    columns: tuple[Column, ...]

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]

    def column(self, name: str) -> Column:
        for c in self.columns:
            if c.name == name:
                return c
        raise KeyError(f"{self.name} has no column {name!r}")


def _c(name, dtype, unit, description, producer, nullable=False, allowed=None) -> Column:
    return Column(name, dtype, unit, description, producer, nullable, allowed)


FLIGHTS = Table(
    name="flights",
    row="one flight (R1-R7, 196 rows; ground and hover tests excluded)",
    filename="flights.parquet",
    key=("flight",),
    columns=(
        _c("flight", INT, "", "Flight number", DATA),
        _c("route", STR, "", "Route R1-R7", DATA, allowed=ROUTES),
        _c("payload_g", INT, "g", "Payload: 0, 250, 500 (750 for flight 76)", DATA),
        _c("speed_mps", INT, "m/s", "Target cruise speed, 4-12", DATA),
        _c("altitude_m", FLOAT, "m", "Target altitude; missing for R7", DATA, nullable=True),
        _c("variable_altitude", BOOL, "", "Stepped altitude profile (R7)", DATA),
        _c("start_time", DATETIME, "", "Local start date and time, typos corrected", DATA),
        _c("local_time_raw", STR, "", "Start time as written in parameters.csv", DATA),
        _c("time_corrected", BOOL, "", "Start time was corrected", DATA),
        _c("in_design", BOOL, "", "R1 with payload 0/250/500: used by experiment charts", DATA),
        _c("is_outlier", BOOL, "", "Flagged by the outlier rule (D4)", DATA),
        _c("outlier_reason", STR, "", "Why the flight is flagged", DATA, nullable=True),
        _c("duration_s", FLOAT, "s", "Flight duration", DATA),
        _c("distance_m", FLOAT, "m", "Distance travelled, from GPS", DATA),
        _c("energy_wh", FLOAT, "Wh", "Total energy, integrated at the raw rate", DATA),
        _c("wh_per_km", FLOAT, "Wh/km", "Energy per kilometre", DATA),
        _c("mean_power_w", FLOAT, "W", "Mean power over the whole flight", DATA),
        _c("start_voltage_v", FLOAT, "V", "Battery voltage before take-off", DATA),
        _c("end_voltage_v", FLOAT, "V", "Battery voltage after landing", DATA),
        _c("voltage_drop_v", FLOAT, "V", "start_voltage_v - end_voltage_v", DATA),
        _c("mean_airspeed_mps", FLOAT, "m/s", "Mean anemometer reading (not wind, D3)", DATA),
        _c("sample_count", INT, "", "Number of raw samples", DATA),
        _c("max_gap_s", FLOAT, "s", "Longest interval between raw samples", DATA),
        _c("large_gap_count", INT, "", "Intervals longer than 1 s", DATA),
        _c("cruise_power_w", FLOAT, "W", "Mean power in the Cruise phase (RF target)", PLATFORM),
        _c("climb_power_w", FLOAT, "W", "Mean power in the Climb sub-phase", PLATFORM),
        _c("wp_turn_count", INT, "", "Number of WP turns found by the phase rule", PLATFORM),
    ),
)

TELEMETRY = Table(
    name="telemetry_1hz",
    row="one second of one flight (resampled to 1 Hz after energy integration)",
    filename="telemetry_1hz.parquet",
    key=("flight", "t_s"),
    columns=(
        _c("flight", INT, "", "Flight number", DATA),
        _c("t_s", FLOAT, "s", "Time since the first sample of the flight", DATA),
        _c("t_since_takeoff_s", FLOAT, "s", "Time since take-off; negative before", PLATFORM),
        _c("lat_deg", FLOAT, "deg", "Latitude", DATA),
        _c("lon_deg", FLOAT, "deg", "Longitude", DATA),
        _c("east_m", FLOAT, "m", "East of the R1 home point", DATA),
        _c("north_m", FLOAT, "m", "North of the R1 home point", DATA),
        _c("alt_rel_m", FLOAT, "m", "Altitude above the take-off point", DATA),
        _c("ground_speed_mps", FLOAT, "m/s", "Horizontal speed over ground", DATA),
        _c("vertical_speed_mps", FLOAT, "m/s", "Vertical speed, up is positive", DATA),
        _c("course_deg", FLOAT, "deg", "Course over ground from GPS, 0 = north", DATA),
        _c("airspeed_mps", FLOAT, "m/s", "Anemometer reading: 'airspeed (anemometer)'", DATA),
        _c("voltage_v", FLOAT, "V", "Battery voltage", DATA),
        _c("current_a", FLOAT, "A", "Battery current, negative values clipped to 0", DATA),
        _c("power_w", FLOAT, "W", "Battery power = voltage x current", DATA),
        _c("energy_wh", FLOAT, "Wh", "Energy used since the first sample", DATA),
        _c("phase", STR, "", "Estimated main phase", PLATFORM, allowed=PHASES),
        _c("sub_phase", STR, "", "Estimated sub-phase", PLATFORM, allowed=SUB_PHASES),
    ),
)

PHASE_ENERGY = Table(
    name="phase_energy",
    row="one sub-phase of one flight",
    filename="phase_energy.parquet",
    key=("flight", "sub_phase"),
    columns=(
        _c("flight", INT, "", "Flight number", PLATFORM),
        _c("phase", STR, "", "Estimated main phase", PLATFORM, allowed=PHASES),
        _c("sub_phase", STR, "", "Estimated sub-phase", PLATFORM, allowed=SUB_PHASES),
        _c("energy_wh", FLOAT, "Wh", "Energy used in this sub-phase", PLATFORM),
        _c("duration_s", FLOAT, "s", "Time spent in this sub-phase", PLATFORM),
    ),
)

WAYPOINTS = Table(
    name="waypoints",
    row="one turning point of one flight (index 0 = home)",
    filename="waypoints.parquet",
    key=("flight", "wp_index"),
    columns=(
        _c("flight", INT, "", "Flight number", PLATFORM),
        _c("wp_index", INT, "", "0 = home (H), then 1, 2, ... in flight order", PLATFORM),
        _c("lat_deg", FLOAT, "deg", "Latitude", PLATFORM),
        _c("lon_deg", FLOAT, "deg", "Longitude", PLATFORM),
        _c("east_m", FLOAT, "m", "East of the R1 home point", PLATFORM),
        _c("north_m", FLOAT, "m", "North of the R1 home point", PLATFORM),
        _c("t_s", FLOAT, "s", "Time of the slowest point of the turn", PLATFORM),
        _c("turn_angle_deg", FLOAT, "deg", "Course change; missing for home", PLATFORM, True),
    ),
)

ML_PAYLOAD = Table(
    name="ml_payload",
    row="one R1 flight with out-of-fold cruise power predictions",
    filename="ml_payload.parquet",
    key=("flight",),
    columns=(
        _c("flight", INT, "", "Flight number", UIML),
        _c("cruise_power_w", FLOAT, "W", "Observed cruise power", UIML),
        _c("rf_pred_w", FLOAT, "W", "Random Forest prediction (model never saw the flight)", UIML),
        _c("linear_pred_w", FLOAT, "W", "Linear regression prediction", UIML),
    ),
)

QUALITY_LOG = Table(
    name="quality_log",
    row="one cleaning rule and its effect",
    filename="quality_log.json",
    key=("rule_id",),
    columns=(
        _c("rule_id", STR, "", "Short code, e.g. R7-altitude", DATA),
        _c("description", STR, "", "What the rule does, one sentence", DATA),
        _c("rows_affected", INT, "", "Raw rows changed or removed", DATA),
        _c("flights_affected", INT, "", "Flights changed, flagged or removed", DATA),
        _c("iso25012", STR, "", "ISO/IEC 25012 quality characteristic", DATA, allowed=ISO25012),
    ),
)

TABLES: dict[str, Table] = {
    t.name: t for t in (FLIGHTS, TELEMETRY, PHASE_ENERGY, WAYPOINTS, ML_PAYLOAD, QUALITY_LOG)
}

PRODUCER_LABEL = {DATA: "Data (preprocess)", PLATFORM: "Platform (phases)", UIML: "UI & ML"}


def data_dictionary() -> list[dict[str, str]]:
    """Rows for the Data Quality section's data dictionary (one row per column)."""
    return [
        {
            "table": t.name,
            "column": c.name,
            "type": c.dtype,
            "unit": c.unit,
            "description": c.description,
            "produced by": PRODUCER_LABEL[c.producer],
        }
        for t in TABLES.values()
        for c in t.columns
    ]
