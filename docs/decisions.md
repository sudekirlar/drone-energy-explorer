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

## D11 · Sections switched with a menu, not tabs
- **Decision:** `st.segmented_control` at the top; only the selected section runs. Each chart card is
  an `@st.fragment`; heavy work is cached with `@st.cache_data`.
- **Alternative:** `st.tabs`.
- **Why:** `st.tabs` executes every tab on every rerun. With a menu and fragments a card's own control
  reruns only that card.
