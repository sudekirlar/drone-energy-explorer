# Decision log

One entry per decision that affects the team: what we decided, what we considered instead, and why.
Newest at the bottom. Reference an entry in PRs and the report as `D<n>`.

---

## D1 · Calendar heatmap → flight × time heatmap
- **Decision:** a heatmap with one row per flight and one column per 2 s slice (chart 10), rows
  sortable by altitude, speed, payload or K-means cluster.
- **Alternative:** calendar heatmap (day × start hour, colour = energy residual).
- **Why:** only 16 of the 214 days in the collection period have flights (Lecture 5: a heatmap needs
  its cells filled), and the day effect is not significant (Kruskal-Wallis, p ≈ 0.09). The "no day
  effect" finding moves to the Data Quality section as one sentence.

## D2 · Space-Time Cube: time by default, altitude on demand
- **Decision:** chart 2 is a 3D Space-Time Cube; the vertical axis is time since take-off by
  default and altitude as an option. No top-down view.
- **Alternative:** a 3D trajectory with altitude only.
- **Why:** the map (chart 1) loses two real dimensions, time and altitude. The time axis shows
  tempo and waypoint pauses (4 vs 12 m/s); the altitude axis shows the climb and R7's stepped
  ascent. Both earn the cost of 3D (occlusion, perspective; Lecture 7). The top-down view would
  duplicate the map.

## D3 · The "wind" column is airspeed, not wind
- **Decision:** wind is removed from the research question. `wind_speed` is shown only as
  "airspeed (anemometer)" in the timeline and kept out of multivariate charts and both models.
- **Why:** it is the anemometer on the drone. Flight means correlate 0.94 with the target speed,
  and during motion it moves with ground speed and reads on average 1.8 m/s higher. Using it as
  wind would add a copy of speed and produce a false "wind costs energy" finding.

## D4 · Outlier rule: joint deviation
- **Decision:** flag flights by their joint deviation across flight-level measures; flagged
  flights stay in the data with a flag and a sidebar checkbox hides them.
- **Alternative:** per-configuration MAD on Wh/km; IQR on telemetry rows.
- **Why:** with about three repeats per configuration, MAD flagged 23 flights; the joint deviation
  flags 4, including the known high-wind flight 129. Row-level IQR flags take-off and landing
  transients, which are real, not errors.
- **Update (2026-11-14):** the rule as implemented in `preprocess.py` flags **15** flights, all
  R1 design flights, including 129 and 85. The prototype's 4 came from a different definition and
  is not comparable. "Hide outlier flights" in the sidebar therefore hides 15 flights; the
  README and the Data Quality section use 15.

## D5 · Second ML algorithm: Random Forest regression of cruise power
- **Decision:** predict cruise power (W) from payload, speed and altitude; one row per flight;
  5-fold CV × 5 seeds, compared with linear regression and with a test grouped by configuration.
  Shown in chart 6 (observed / predicted / difference views).
- **Alternative:** a payload classifier shown as a ternary plot.
- **Why:** the research question is about how flight conditions shape energy, and a regression on
  the controlled variables answers it directly. Cruise power is not affected by take-off and
  landing time, so it isolates payload and speed. The comparison with a linear model shows what
  the forest adds: the U-shaped speed effect (jump at 12 m/s). Anemometer left out (D3); start
  voltage was tried and added nothing.

## D6 · Estimated flight phases and their validation
- **Decision:** a rule assigns every sample to one of 4 main phases (take-off, cruise, manoeuvre,
  landing) and 7 sub-phases. The dashboard calls them "estimated phases".
- **Why:** the data has no phase labels. Three checks make the rule defensible: energy
  conservation (phase energies sum to the flight total), mission geometry (about 90 % of R1
  flights show exactly the two expected waypoint turns), and threshold sensitivity (take-off and
  landing shares move by under 1 point; the cruise/manoeuvre boundary moves 2–5 points, so those
  shares are reported as ranges). Acceleration and deceleration are merged into "speed change"
  because they could not be separated reliably.

## D7 · Ten charts and the advanced count
- **Decision:** ten charts. Certain advanced (named in the assignment): route map, Sankey,
  treemap family, parallel coordinates. Candidates: Space-Time Cube, SPLOM, flight × time heatmap.
  Basic: timeline, payload × speed heatmap, violin.
- **Why:** six advanced charts are required; two of the three candidates are enough, so one
  rejection still leaves the requirement met. Space-Time Cube and SPLOM are asked to the
  instructor early (task K1). Connected scatterplot and ternary plot were dropped from earlier
  drafts.

## D8 · Roles
- **Decision:** Platform (Sude), Data (İlayda), UI & ML (Pelin); each also owns one dashboard
  section. Details in CONTRIBUTING.md.
- **Alternative:** one person doing all data preparation.
- **Why:** data preparation is the longest critical task; splitting cleaning (Data) from phases
  (Platform) lets both run in parallel and check each other through the energy conservation test.
  Every member has a visible section for the individually graded presentation.

## D9 · Repo, deployment and live link on one account
- **Decision:** the repository and the Streamlit Community Cloud app live on the Platform owner's
  account; the app is deployed on day one from a placeholder `app.py`.
- **Why:** deployment settings, logs and reboots stay with one person, and deployment problems show
  up on the first day instead of the last.

## D10 · Python 3.13 and pinned versions
- **Decision:** Python 3.13 for everyone and on Streamlit Cloud; exact pins in `requirements.txt`
  (runtime) and `requirements-dev.txt` (tests, lint, hooks).
- **Alternative:** Python 3.11 (earlier plan), 3.12 (first choice on day one), or unpinned latest.
- **Why:** numpy 2.5 requires Python ≥ 3.12, which rules out 3.11. PyCharm on Windows rejected the
  3.12 virtual environment, while 3.13 was already installed. The pinned set was installed and
  smoke-tested on 3.12 and 3.13 on 2026-11-12. Community Cloud has been reported to run a
  different Python than selected, so the placeholder page prints the running version.
- **Update (2026-11-13):** Streamlit Cloud replaced our pinned pyarrow 26.0.1 with 24.0.0 at
  deploy time, citing a known segfault (apache/arrow#50471). We pin 24.0.0 so local, CI and
  Cloud run the same version.

## D11 · Sections switched with a menu, not tabs
- **Decision:** `st.segmented_control` at the top; only the selected section runs. Each chart card is
  an `@st.fragment`; heavy work is cached with `@st.cache_data`.
- **Alternative:** `st.tabs`.
- **Why:** `st.tabs` executes every tab on every rerun. With a menu and fragments a card's own control
  reruns only that card.

## D12 · Column names: lowercase, unit at the end
- **Decision:** every column in the data contract is lowercase snake case with the unit as the last
  part: `power_w`, `energy_wh`, `wh_per_km`, `alt_rel_m`, `speed_mps`. Raw CMU names
  (`battery_voltage`, `wind_speed`, ...) are translated only in `preprocess.py`.
- **Alternative:** units in their SI spelling (`power_W`, `energy_Wh`), as in the first plan.
- **Why:** the preprocessing code and its tests already used lowercase names; lowercase is the
  Python convention and what code assistants produce by default; mixing `W` and `w` is an easy
  mistake to miss. One translation point keeps raw names out of every chart.

## D13 · Loader without Streamlit, caching in the UI layer
- **Decision:** `src/data/loader.py` reads and validates tables with plain pandas; `@st.cache_data`
  wraps it in `app.py`. The loader prefers `data/processed/` and falls back to `data/sample/`.
- **Alternative:** `@st.cache_data` inside `loader.py` (first plan).
- **Why:** keeps the layer rule (no Streamlit in `src/data`, enforced by a test) and makes the
  loader testable without a browser. The fallback lets charts start on sample tables and switch
  to real data without code changes.

## D14 · How the phase rule is implemented
- **Decision:** (1) a leg's direction is the line from its first to its last point, not the
  per-sample GPS course; (2) sloped cruise is searched in every horizontal motion (ground speed
  ≥ 1.5 m/s), not only in legs at 80 % of the target speed; (3) `phase_energy` has one row per
  flight and sub-phase, all eight, zeros and Ground included; (4) the energy between two samples
  is booked to the first sample's sub-phase.
- **Why:** (1) samples are 0.1–0.2 s apart, so their course is mostly GPS noise and reads 0°
  when the drone stands still; (2) on R7 the drone flies its climbing legs at ~8 m/s and the
  descending leg at ~5 m/s against a 10 m/s target; (3) averages over flights must count an
  absent sub-phase as zero, and the parts must add up to the flight total; (4) makes energy
  conservation exact.
- **Result on the real data:** largest gap between phase energies and flight energy 7e-14 Wh;
  178 of 181 R1 design flights show exactly two WP turns (the others are 85, 86 and 129; 85 and
  129 are flagged outliers, 86 never holds 80 % of its 12 m/s target on two legs); every R6
  flight shows three turns, though the third is only 47–49°; sloped cruise appears only in
  flights 2, 278 and 279. Changing the cruise-speed ratio to 70 % / 90 % moves the cruise and
  manoeuvre shares by 2.2–4.1 points; ±20 % on every other threshold moves take-off and landing
  by under 0.4 points.

## D15 · One pipeline writes data/processed, and its files are committed
- **Decision:** `src/data/pipeline.py` runs cleaning (Data, writes `data/intermediate/`), phases
  (Platform) and the contract check, and is the only code that writes the contract tables to
  `data/processed/`. The processed tables (about 4 MB) are committed to git. The T5 sample
  tables stay in `data/sample/` as a fallback.
- **Alternative:** each producer writes its part of `flights` and `telemetry_1hz` to
  `data/processed/` in turn.
- **Why:** the Data columns and the Platform columns live in the same tables, which pass the
  contract only when both are filled, so one step validates and writes them together;
  Streamlit Cloud has no raw data, so it can only read committed tables.

## D16 · Energy section: what each chart leaves out, and why
- **Sankey (chart 4):** the Ground sub-phase is not drawn (motors idle on the ground, under 1 %
  of any flight; the About text says so). Altitude, speed and payload compare only R1 design
  flights; "Route" uses every filtered flight. A "percent" toggle was tried and removed: it only
  equalised the group nodes, while the hover and the finding already give shares. The middle and
  right nodes are sums over the groups, so their hover gives the mean over the groups instead.
- **Treemap (chart 5):** size is the number of flights and is nearly equal by design; colour
  (median Wh/km) carries the result. The level order is a menu because the hierarchy is ours.
  Icicle and sunburst open two levels deep, because 60 leaves were unreadable as thin rows.
- **Payload x speed heatmap (chart 6):** the card's own altitude menu from the chart guide was
  dropped, because the sidebar already filters altitude and two filters could contradict each
  other. The two power views share one colour scale and the two difference views share another,
  so switching views compares like with like. The finding leads with the shape across speed;
  the payload effect is the violin's finding (chart 9).
- **Colour and contrast:** Sankey bands use opacity 0.55, because at 0.35 the take-off and cruise
  bands came too close under simulated protanopia and tritanopia (CIELAB distance about 8; at
  0.55 every main-phase pair stays above 12 in both themes). Sankey node labels take the page's
  text colour through CSS, and heatmap cell text is dark or white by the cell's lightness,
  because Streamlit's chart theme gives all chart text one mid-grey colour.
- **Uncertainty:** heatmap hovers give the spread of the measured flights in each cell
  (standard deviation); treemap hovers give the middle half of the flights (25th to 75th
  percentile) from three flights up.

## D17 · The pipeline re-runs the regression; its tests use one seed
- **Decision:** `pipeline.py` ends by re-evaluating the regression (`regressor.py`) on the
  flights table it has just written, and rewrites `ml_payload` and `ml_metrics.json`
  (`--skip-model` turns this off). The regressor's tests evaluate once, with one seed, and share
  the result.
- **Why:** without the step, a rebuilt `flights` table would sit next to predictions made from
  the old one. Five seeds only make the published scores steadier; the behaviour the tests
  check is the same with one seed, and the test suite went from about 70 s to about 10 s.
