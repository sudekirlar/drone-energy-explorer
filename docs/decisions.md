# Decision log

One entry per decision that affects the team: what we decided, what we considered instead, and why.
Newest at the bottom. Reference an entry in PRs and the report as `D<n>`.

---

## D1 · Calendar heatmap → flight × time heatmap
- **Decision:** a heatmap with one row per flight and one column per time slice.
- **Alternative:** calendar heatmap (day × start hour, colour = energy residual).
- **Why:** only 16 of the 214 days in the collection period have flights (93 % empty; Lecture 5:
  calendar views need a mostly complete field), and the day effect is not significant (p ≈ 0.09).
  The "no day effect" finding moves to the Data Quality section as one sentence.

## D2 · Connected scatterplot axes: current × voltage
- **Alternative:** voltage × cumulative energy.
- **Why:** cumulative energy only increases, so no loops form. Current × voltage shows the battery's
  internal resistance and discharge under load.

## D3 · Why 3D: altitude
- **Decision:** vertical axis defaults to altitude, optionally time. No "view from above" preset.
- **Why:** the most expensive phases and the variable-altitude R7 flights are invisible in 2D. The 2D
  view is left to the route map to avoid two charts showing the same thing.

## D4 · Outlier rule: joint deviation
- **Decision:** flag flights by their joint deviation across flight-level measures.
- **Alternative:** per-configuration MAD on Wh/km.
- **Why:** with n = 3 repeats per configuration, MAD flagged 23 flights; the joint deviation flags 4,
  including the known high-wind flight 129. Flagged flights stay in the data with a flag.

## D5 · ML view: ternary plot
- **Decision:** the Random Forest is shown as a ternary plot of the three payload probabilities;
  confusion matrix and feature importance are small summaries next to it.
- **Why:** the three class probabilities sum to 1, which is exactly the structure a ternary plot
  assumes. It shows uncertainty per flight (Guideline #10) instead of a single accuracy number.

## D6 · Roles
- **Decision:** Platform (Sude), Data (İlayda), UI & ML (Pelin); each also owns one dashboard
  section of three charts. Details in CONTRIBUTING.md.
- **Alternative:** one person doing all data preparation.
- **Why:** data preparation is the longest critical task; splitting cleaning (Data) from phases
  (Platform) lets both run in parallel and check each other through the energy conservation test.
  Every member has a visible section for the individually graded presentation.

## D7 · Repo, deployment and live link on one account
- **Decision:** the repository and the Streamlit Community Cloud app live on the Platform owner's
  account; the app is deployed on day one from a placeholder `app.py`.
- **Why:** deployment settings, logs and reboots stay with one person, and deployment problems show
  up on the first day instead of the last.

## D8 · Python 3.13 and pinned versions
- **Decision:** Python 3.13 for everyone and on Streamlit Cloud; exact pins in `requirements.txt`
  (runtime) and `requirements-dev.txt` (tests, lint, hooks).
- **Alternative:** Python 3.11 (earlier plan), 3.12 (first choice on day one), or unpinned latest.
- **Why:** numpy 2.5 requires Python ≥ 3.12, which rules out 3.11. We started on 3.12, but PyCharm
  on Windows rejected the 3.12 virtual environment as an invalid SDK while 3.13 worked, so we moved
  to 3.13. The pinned set was installed and smoke-tested on both 3.12 and 3.13 (all nine chart
  types, `st.fragment`, `st.segmented_control`) on 2026-11-12. Community Cloud has been reported to
  run a different Python than selected, so the placeholder page prints the running version and we
  check it on the live link.

## D9 · Sections switched with a menu, not tabs
- **Decision:** `st.segmented_control` at the top; only the selected section runs. Each chart card is
  an `@st.fragment`; heavy work is cached with `@st.cache_data`.
- **Alternative:** `st.tabs`.
- **Why:** `st.tabs` executes every tab on every rerun. With a menu and fragments a card's own control
  reruns only that card.
