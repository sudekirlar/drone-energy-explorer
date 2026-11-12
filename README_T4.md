# T4 — Streamlit App Skeleton

This is a drop-in T4 scaffold for Drone Delivery Energy Explorer.

## Included
- `app.py`: Streamlit entry point, page config, cached loading, shared sidebar, section navigation.
- `src/data/filters.py`: immutable `FilterState` and shared `apply_filters()`.
- `src/theme.py`: Viridis, phase, payload, categorical and diverging palettes plus Plotly template.
- `src/sections/`: four modules, each with `render(df, filters)`.
- `src/sections/common.py`: example card with selectbox, Plotly chart and finding box.

## Data contract
Preferred input: processed flight-level `data/flight_summary.csv`. Fallback: `data/flights.csv`.
The loader does not recalculate power, energy or estimated flight phases. Use the validated T0/T1 output.

Filter aliases supported: payload/payload_g, target_altitude/altitude, target_speed/speed, route, flagged.

## Demo data
If no CSV exists in `data/`, `src/data/demo.py` generates **synthetic placeholder data** and the app shows a warning banner. Drop the real `data/flight_summary.csv` in and the banner disappears automatically.

## Run
```bash
pip install -r requirements-t4.txt
streamlit run app.py
```

## Integration notes
1. Merge this scaffold with the current main branch; do not blindly overwrite T0/T1 files.
2. If the team already has a loader, adapt `src/data/loader.py` to call its public function.
3. Keep section signatures as `render(df, filters)` and use the shared filtered frame.
4. Import `PALETTES` / `plotly_template` from `src.theme` for consistent visuals.
5. Label phases as estimated. `wind_speed` is anemometer airspeed, not ambient wind.
6. Source energy calculations from preprocessing; telemetry timestamps are irregular, so do not assume 1 Hz.
