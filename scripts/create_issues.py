"""Create the project's labels, milestone and task issues on GitHub (run once, by Platform).

Needs the GitHub CLI, logged in:  gh auth login
Run from the repo root:           python scripts/create_issues.py --dry-run   (preview)
                                  python scripts/create_issues.py             (create)
With a GitHub Project board:      gh auth refresh -s project                  (once)
                                  python scripts/create_issues.py --project 1
  -> also adds every issue to project #1 and fills Status, Day and Estimate (h).

Tasks follow the approved project plan (proje_plani) and chart guide ("On grafik, tek soru").
An issue a teammate already opened for a task can be adopted instead of duplicated:
                                  python scripts/create_issues.py --project 14 --adopt T2=1
  -> issue #1 gets the task's title, labels, milestone and assignee; the plan's checklist is added
     as a comment, so the author's own text stays untouched.

Safe to re-run: labels are updated in place, and an issue whose title already exists is skipped.
Assignment needs the teammates to have accepted the collaborator invitation; if it fails, the issue
is created unassigned and a warning is printed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

# ---- fill in ------------------------------------------------------------------------------------
GH_USER = {
    "platform": "sudekirlar",
    "data": "ilayda-demir",
    "uiml": "Pelingulkizilkilic",
}
MILESTONE = "v1.0 submission"
MILESTONE_DUE = "2026-11-15T20:59:59Z"  # 23:59 Istanbul time
# -------------------------------------------------------------------------------------------------

LABELS = {
    # role
    "role: platform": ("c2621f", "Sude: repo, contract, phases, deploy"),
    "role: data": ("7a5195", "İlayda: cleaning, tests, data quality"),
    "role: ui-ml": ("1b8a66", "Pelin: app frame, theme, models"),
    "role: all": ("6b6860", "Whole team"),
    # kind
    "setup": ("bfd4f2", "Repo, tooling, contract"),
    "data": ("d4c5f9", "Preprocessing, tables, tests"),
    "ml": ("c2e0c6", "Models and evaluation"),
    "chart": ("fef2c0", "A dashboard visualization"),
    "deploy": ("f9d0c4", "Streamlit Cloud, release"),
    "quality": ("e6e6e6", "Consistency, evaluation, user test"),
    "docs": ("0075ca", "README, report, decisions, slides"),
    "contract": ("b60205", "Changes src/data/schema.py; needs Platform + producer approval"),
    # priority
    "critical path": ("1d1c1a", "Delays the submission if late"),
    "must": ("2d7a3e", "Required for submission"),
    "should": ("2a6fb0", "Strongly recommended"),
    "later": ("ededed", "Idea parked until Saturday"),
}

SECTION = {
    "A": "Flight & Temporal Analysis",
    "B": "Energy & Experimental Conditions",
    "C": "Multivariate Analysis & ML",
}
SECTION_ROLE = {"A": "data", "B": "platform", "C": "uiml"}
ROLE_LABEL = {"platform": "role: platform", "data": "role: data", "uiml": "role: ui-ml"}

# Target day (= on main by the end of that day) and estimate per person in hours, from the plan.
# The plan was one day behind on Thu 12: Wednesday's work moved to Thursday, and Friday takes both
# Thursday's and Friday's work so Saturday stays free for quality. Edit freely on the board.
DAYS = ["Thu 12", "Fri 13", "Sat 14", "Sun 15", "After submission"]
PLAN = {
    "T0": ("Thu 12", 1.25), "K1": ("Thu 12", 0.2), "T1": ("Thu 12", 0.75), "T5": ("Thu 12", 0.5),
    "T4": ("Thu 12", 1.0), "T2": ("Fri 13", 1.5), "T6": ("Fri 13", 1.75), "T3": ("Fri 13", 0.5),
    "E1": ("Fri 13", 1.25), "C2": ("Fri 13", 0.75), "C1": ("Fri 13", 1.5), "G1": ("Fri 13", 1.75),
    "G2": ("Fri 13", 1.5), "G3": ("Fri 13", 1.25), "G4": ("Fri 13", 1.75), "G5": ("Fri 13", 1.0),
    "G6": ("Fri 13", 1.25), "G7": ("Fri 13", 1.5), "G8": ("Fri 13", 1.0), "G9": ("Fri 13", 0.75),
    "G10": ("Sat 14", 1.25), "E3": ("Fri 13", 0.5), "E2": ("Fri 13", 1.25), "Q1": ("Sat 14", 1.0),
    "Q2": ("Sat 14", 1.0), "Q3": ("Sat 14", 0.5), "E4": ("Sat 14", 0.75), "D4": ("Sat 14", 0.5),
    "D2": ("Sat 14", 0.3), "D3": ("Sat 14", 0.3), "D1": ("Sun 15", 1.0), "R1": ("Sun 15", 0.75),
    "P1": ("Sun 15", 1.5), "S1": ("Sun 15", 0.25), "P2": ("After submission", 1.0),
}  # fmt: skip

# id, title, role, kind, priority, why, steps, depends, produces, done
# role: platform | data | uiml | all | section:A/B/C
# fmt: off
TASKS = [
    ("T0", "Repo setup and first deployment", "platform", "setup", "critical path",
     "Everyone works with the same structure, rules and library versions, and the live link exists "
     "from day one so deployment problems surface early.",
     ["Public repo, two collaborators invited", "Everyone's git e-mail matches their GitHub e-mail",
      ".gitignore, pinned requirements (runtime + dev), folder skeleton",
      "README skeleton, CONTRIBUTING, PR and issue templates, CODEOWNERS, decision log",
      "pre-commit + ruff, CI workflow, architecture test",
      "First commits directly on main, including a placeholder app.py",
      "Deploy on Streamlit Community Cloud (Python 3.13), live link in README",
      "Then protect main: PR required, 1 approval, CI must pass, no force push, no bypass; "
      "merge commits only; auto-delete branches",
      "Labels, milestone, Projects board and one issue per task"],
     "-", ["Working repo", "Live link (placeholder page)", "Issue list"],
     ["Live link opens and shows Python 3.13", "All three cloned the repo; pip install and "
      "pre-commit install work", "A direct push to main is rejected"]),
    ("K1", "Ask the instructor whether Space-Time Cube and SPLOM count as advanced", "data",
     "docs", "should",
     "Four charts are certainly advanced (map, Sankey, treemap, PCP). Space-Time Cube, SPLOM and the "
     "flight x time heatmap are candidates; two of the three are needed. Asking early leaves time "
     "to strengthen a chart.",
     ["Short English e-mail: 'Can we count a space-time cube and a scatterplot matrix (with "
      "brushing) as advanced?' with one sentence each on why",
      "Record the answer in docs/decisions.md (D7)"],
     "-", ["Instructor's answer"], ["E-mail sent; answer recorded"]),
    ("T1", "Data contract and loading layer", "platform", "setup", "critical path",
     "Charts and ML must not wait for preprocessing; everyone codes against the same column names, "
     "types and units.",
     ["src/data/schema.py: columns, dtype and unit per table (flights, telemetry_1hz, phase_energy, "
      "waypoints, ml_payload, quality_log); SCHEMA_VERSION",
      "docs/interfaces.md: chart function signature, section render(), session_state keys",
      "src/data/loader.py: plain-pandas readers that validate columns against schema.py; "
      "data/sample until data/processed exists (caching happens in app.py)",
      "Review by Data and UI & ML"],
     "T0", ["src/data/schema.py", "src/data/loader.py", "docs/interfaces.md"],
     ["Data and UI & ML approved", "loader reads the sample tables (after T5)"]),
    ("T5", "Sample tables that follow the contract", "data", "data", "critical path",
     "Lets charts and the app skeleton start before cleaning is finished (mock-API idea).",
     ["~15 R1 flights covering every payload, altitude and speed level, plus one R6 and one R7",
      "flights, telemetry_1hz, phase_energy, waypoints, ml_payload (fake predictions, clearly "
      "marked as sample)", "Write to data/sample/"],
     "T1", ["data/sample/*.parquet"],
     ["loader reads every sample file", "Column names identical to schema.py"]),
    ("T4", "App skeleton: menu, sidebar filters, theme, example card", "uiml", "setup",
     "critical path",
     "The frame everyone plugs their charts into, and the shared visual language of the ten "
     "charts. The example card is the template newcomers to Streamlit copy.",
     ["app.py on top of the placeholder: page config, cached loading via loader.py",
      "Sidebar: payload, altitude, speed, hide flagged, include R2-R7 -> FilterState",
      "src/data/filters.py: apply_filters()",
      "Top menu with st.segmented_control -> section render()",
      "src/theme.py: palettes (Viridis, phase colours, payload tones, categorical, diverging) and "
      "one Plotly template",
      "Four section files with render(): overview, flight_temporal, energy, multivariate_ml",
      "Example card: @st.fragment + selectbox + st.plotly_chart + Finding box",
      "Overview KPI: number of filtered flights"],
     "T0, T1", ["app.py", "src/theme.py", "src/data/filters.py", "src/sections/*.py"],
     ["streamlit run app.py switches sections", "Changing a filter changes the KPI"]),
    ("T2", "Cleaning and flight summaries", "data", "data", "critical path",
     "All charts are fed by these tables; this is the assignment's cleaning/outlier requirement.",
     ["Read the 209 flight CSVs + parameters.csv",
      "Table rules: R7 altitude, flight 76 flag, four start-time typos (keep raw), A/H split",
      "Telemetry: clip current at 0, power_W = V x I, alt_rel_m, ground speed -> clean_telemetry() "
      "on main early (phases build on it)",
      "Total energy at raw rate with real dt (trapezoid) BEFORE resampling",
      "Flight summaries: energy, distance, Wh/km, duration, voltages, anemometer mean",
      "Outlier rule (joint deviation, D4) + cruise altitude check",
      "Resample to 1 Hz; write flights, telemetry_1hz",
      "quality_log.json: rule, description, rows/flights affected, ISO 25012 category"],
     "T1 (raw reading can start before)",
     ["src/data/preprocess.py", "flights, telemetry_1hz", "quality_log.json"],
     ["python -m src.data.preprocess finishes in under a minute",
      "Sanity: 181 R1 flights, R1 median energy ~21 Wh, 4 outliers incl. 129",
      "App switches from sample to processed data with one line"]),
    ("T6", "Flight phases, phase energy, waypoints", "platform", "data", "critical path",
     "Estimated phases are the dashboard's core concept: Sankey, timeline phase bands, violin, "
     "flight x time heatmap and the map's waypoint markers depend on them.",
     ["Rule (chart guide): P < 60 W ground; vz > 0.5 and ground speed < 1.5 climb; ground speed "
      ">= 0.8 x target cruise; segments < 2 s merged into the previous one",
      "4 main phases / 7 sub-phases: take-off (spool-up, climb) | cruise (straight leg, sloped "
      "cruise) | manoeuvre (WP turn > 45 deg from GPS course, speed change) | landing (descent "
      "incl. touchdown)",
      "Prototype on raw data until clean_telemetry() is on main, then switch to it",
      "Energy per phase at raw rate with real dt -> phase_energy",
      "Waypoints: slowest point of each WP turn -> waypoints",
      "Phase column in telemetry; cruise and climb power in flight summaries",
      "Validation note for report and Data Quality: share of R1 flights with exactly 2 WP turns "
      "(~90 %), threshold sensitivity table"],
     "T1; clean_telemetry() from T2", ["src/data/phases.py", "phase_energy, waypoints"],
     ["Sum of phase energies = total energy for every flight (T3)",
      "Every flight has a take-off and a landing",
      "Sloped cruise only in flight 2 and R7 flights 278/279"]),
    ("T3", "Data tests", "data", "data", "should",
     "Proves the cleaning and the phase rule are right; the Sankey rests on energy conservation.",
     ["Row and flight counts (257,896 raw rows, 209 records)",
      "Ranges: voltage ~18-27 V, current >= 0, coordinates inside the field",
      "Energy conservation per flight (small tolerance)",
      "At least one take-off and one landing per flight",
      "At least 85 % of R1 flights have exactly 2 WP turns"],
     "T2, T6", ["tests/test_data.py"], ["pytest green locally and in CI"]),
    ("E1", "Overview & Data Quality section", "data", "quality", "must",
     "On-screen evidence for the cleaning requirement.",
     ["KPI row: flights, total flight time, total distance, median energy",
      "Data source and context paragraph (CMU, Matrice 100, limits of generalisation)",
      "ISO/IEC 25012 table", "Cleaning log from quality_log.json", "Data dictionary (expander)",
      "One sentence: no significant day effect (D1); 'wind' is airspeed (D3)"],
     "T2", ["src/sections/overview.py"], ["English; numbers come from quality_log automatically"]),
    ("C2", "K-means module", "uiml", "ml", "must",
     "First ML algorithm; colours the PCP, and SPLOM and the flight x time heatmap use the same "
     "clusters.",
     ["run_kmeans(flights, k) -> labels + silhouette",
      "Five standardised outcome measures: energy, Wh/km, duration, cruise power, climb power; "
      "no anemometer (copy of speed)",
      "Labels ordered by energy (G1 = lowest) so colours stay stable when k changes",
      "n_init=20, fixed random_state"],
     "T1, T5 (starts on sample data)", ["src/ml/clustering.py"],
     ["Silhouette for k=3 ~0.32 (prototype); cluster 1 has no 500 g flight"]),
    ("C1", "Random Forest regression of cruise power (offline part)", "uiml", "ml", "must",
     "Second ML algorithm: predicts cruise power from flight conditions. One row per flight; the "
     "cross-validation runs once, not in the app.",
     ["Target: cruise power (W). Features: payload, speed, altitude. No anemometer (r = 0.94 with "
      "target speed); start voltage tried, adds nothing",
      "R1: 5-fold CV x 5 seeds -> R2 and MAE (mean +- std); out-of-fold prediction per flight",
      "Baseline: linear regression with the same setup",
      "Hard test: CV grouped by configuration (unseen payload-speed-altitude setting)",
      "Permutation importance",
      "ml_payload.parquet (flight, observed, RF prediction, linear prediction) + ml_metrics.json"],
     "T2, T6 (cruise power comes from phases; sample data until then)",
     ["src/ml/regressor.py", "data/processed/ml_payload.parquet", "ml_metrics.json"],
     ["RF R2 ~0.81 +- 0.01, linear ~0.78; grouped test ~0.79 / ~0.76 (prototype)"]),
    ("G1", "Route map", "section:A", "chart", "must",
     "Where on the route is power highest? The assignment's 'geographical map' (certain advanced).",
     ["build_route_map(telemetry, waypoints, flight_ids, color_by): px.scatter_map / line_map, "
      "carto-positron",
      "Home (H) and waypoint markers",
      "Card: route selector (with flight count), flight A/B, colour menu "
      "(power / speed / altitude / phase)",
      "A and B side by side on the same colour scale",
      "Tooltip: time, power, speed, altitude, phase", "Message title + Finding box"],
     "T4 (T6 for waypoints and phase colour)", ["src/charts/route_map.py"],
     ["Works for R1-R7; routes with a single flight handled"]),
    ("G2", "3D Space-Time Cube", "section:A", "chart", "must",
     "The two dimensions the map loses: time and altitude. Advanced candidate (K1).",
     ["build_space_time_cube(telemetry, flight_ids, z_axis, color_by)",
      "Vertical axis: time (default, starts at take-off) / altitude",
      "Colour: phase / altitude / flight / power",
      "Up to 4 flights; default R7 (278) + R1 at 4 m/s (8) and 12 m/s (77)",
      "Good default camera; 'why 3D' line on the card; no top-down preset (the map's job)"],
     "T4", ["src/charts/space_time_cube.py"],
     ["Time axis shows the slope difference of 4 vs 12 m/s; altitude axis shows R7's stepped "
      "climb"]),
    ("G3", "Phase-annotated telemetry timeline", "section:A", "chart", "must",
     "Inside one flight: power, speed, altitude and voltage together; visual check of the phase "
     "rule. Temporal (basic).",
     ["build_timeline(telemetry, flight_id, show_phases): make_subplots, 4 panels, shared time "
      "axis",
      "Speed panel: ground speed + 'airspeed (anemometer)'",
      "Phase bands in the background (add_vrect), WP turns darker",
      "hovermode 'x unified'", "Button to bring the flight over from the map"],
     "T4, T6", ["src/charts/timeline.py"],
     ["Flight 77: speed drops below 1 m/s at WP turns; voltage recovers after landing"]),
    ("G4", "Sankey energy budget", "section:B", "chart", "must",
     "Where does the energy go? The main answer of the dashboard (certain advanced).",
     ["Nodes/links from phase_energy: group -> 4 main phases -> 7 sub-phases",
      "Group menu: altitude / speed / payload / route", "Percent mode",
      "Node positions computed from values (no overlap); zero-value sub-phase nodes not drawn",
      "Card shows the name 'estimated phase', the phase rule and the route-grouping warning",
      "Figure rebuilt from scratch when the group changes (node count changes)"],
     "T6", ["src/charts/sankey.py"],
     ["Consistent with energy conservation; take-off + landing share at 100 m ~54 %; WP-turn "
      "share at 12 m/s ~16 %"]),
    ("G5", "Experiment treemap / icicle / sunburst", "section:B", "chart", "must",
     "Which configuration is cheapest per km? The assignment's 'treemap' (certain advanced).",
     ["build_hierarchy(flights, order, layout): area = flight count, colour = median Wh/km "
      "(colour is essential: the design is balanced, so areas are equal)",
      "Default order payload -> altitude -> speed; route is not a level (R1 only)",
      "Layout menu: treemap / icicle / sunburst; level order menu",
      "Card note: designed hierarchy (Slingsby et al.)"],
     "T4", ["src/charts/treemap.py"], ["Reordering rebuilds the tree; click drills down"]),
    ("G6", "Payload x speed heatmap + Random Forest view", "section:B", "chart", "must",
     "Direct answer to the research question (statistical) and the view of the second ML "
     "algorithm.",
     ["build_payload_speed_heatmap(flights, ml_payload, mode, altitude): 3 payloads x 5 speeds, "
      "colour = mean cruise power, value and flight count in each cell",
      "Show menu: observed / RF prediction / observed - RF / observed - linear (diverging scale, "
      "zero = grey)",
      "Altitude filter",
      "Two small charts below: predicted vs observed, permutation importance",
      "KPIs read from ml_metrics.json"],
     "T4 (C1 for the RF views)", ["src/charts/payload_heatmap.py"],
     ["Linear-difference view: 12 m/s column red; RF difference within +-5 W in every cell"]),
    ("G7", "Parallel coordinates + K-means", "section:C", "chart", "must",
     "Which flights behave alike across all measures? The assignment's 'parallel coordinates' "
     "(certain advanced) and the view of the first ML algorithm.",
     ["build_pcp(flights, labels): 9 axes (no anemometer, voltage drop included) + cluster axis",
      "k slider (2-6); K-means cached", "Silhouette shown on the card",
      "Honest finding text (duration encodes speed indirectly; clusters are not hard categories)"],
     "C2", ["src/charts/pcp.py"],
     ["Axis drag and brushing work; colours stable when k changes"]),
    ("G8", "Scatterplot matrix (SPLOM)", "section:C", "chart", "must",
     "Shape of each pairwise relation; complements the PCP. Advanced candidate (K1).",
     ["build_splom(flights, color_by): speed, cruise power, climb power, Wh/km, voltage drop; "
      "lower triangle, diagonal hidden",
      "Colour menu: payload / K-means cluster / altitude",
      "dragmode='select': flights selected in one panel are highlighted in all panels",
      "Total energy and anemometer left out on purpose (reason on the card)"],
     "T4 (C2 for cluster colour)", ["src/charts/splom.py"],
     ["A box selection in one panel is reflected in the others"]),
    ("G9", "Violin + box of power per phase and payload", "section:C", "chart", "must",
     "Is the payload effect the same in every phase? A different question from the heatmap.",
     ["4 main phases x 3 payloads; tones of one hue per payload", "Show-points checkbox",
      "Note if the axis is cut"],
     "T6", ["src/charts/violin.py"], ["'+250 g ~ +50 W (~10 %)' checked on real data"]),
    ("G10", "Flight x time heatmap", "section:C", "chart", "should",
     "Tenth chart, insurance for the advanced count: 181 flights in one picture, rows sortable by "
     "K-means cluster. Replaces the calendar heatmap (D1).",
     ["build_flight_time_heatmap(telemetry, flights, order, color, include_other_routes)",
      "Row = flight, column = 2 s slice; colour: phase / power",
      "Sort menu: altitude / speed / payload / K-means cluster; group separators and labels",
      "'Include R2-R7' checkbox"],
     "T6, C2", ["src/charts/flight_heatmap.py"],
     ["Phase colouring shows the climb band widening with altitude"]),
    ("E3", "Deployment check with real data", "platform", "deploy", "should",
     "Real data and all libraries load on the cloud for the first time; memory and start-up "
     "problems should show up now, not on Sunday.",
     ["Live link reads data/processed, not data/sample", "Start-up time and memory",
      "Logs free of warnings and errors", "Open on a phone"],
     "T0, T2, T6, T4", ["Live link with real data"],
     ["Opens on phone and laptop with real data"]),
    ("E2", "Links between Flight & Temporal charts", "section:A", "chart", "should",
     "Lecture 9 'connect': map -> Space-Time Cube and timeline.",
     ["session_state keys (map_flights, cube_flights, timeline_flight)",
      "'Send to 3D' and 'Open in timeline' buttons + st.rerun()",
      "Selections survive switching sections"],
     "G1, G2, G3", ["Linking code"], ["Flights sent from the map open in the cube and timeline"]),
    ("Q1", "Consistency pass", "all", "quality", "critical path",
     "Visual consistency and labelling are graded.",
     ["All text in English", "Every title carries a message (Guideline #7)",
      "Units, legends, tooltip formats consistent", "Findings rewritten from real data",
      "Colours only from theme.py", "Colour-blindness emulation (Chrome DevTools)",
      "Cut axes marked"],
     "All charts", ["Fix PRs"], ["Checklist ticked for every card"]),
    ("Q2", "Mini user test", "all", "quality", "should",
     "Lecture 8 subjective feedback; strong evidence in the presentation. Run by Platform and "
     "UI & ML.",
     ["2-3 participants outside the team", "4 concrete tasks",
      "Think-aloud; time and correctness", "At most 3 fixes"],
     "Q1", ["docs/user_test.md"], ["Results and fixes written down"]),
    ("Q3", "RUSTIC table", "uiml", "quality", "should",
     "The instructor's own evaluation framework.",
     ["6 criteria per chart, short note", "What we did about weak criteria"],
     "Q1", ["Table in README or slides"], ["All 10 charts rated"]),
    ("E4", "Final deployment + feature freeze", "platform", "deploy", "critical path",
     "Fix the version that will be submitted.",
     ["All PRs merged", "Click through the live app end to end", "22:00 feature freeze"],
     "Q1", ["Final live link"], ["Live link works on phone and laptop"]),
    ("D4", "Complete the decision log", "all", "docs", "should",
     "The report's 'why these techniques' part and ready answers for questions.",
     ["3-4 lines per decision: what, alternative, why",
      "Each member writes their section's decisions"],
     "-", ["docs/decisions.md"], ["D1-D11 plus the week's decisions"]),
    ("D2", "DATASHEET.md", "data", "docs", "should",
     "Datasheets for Datasets: origin and limits of the data.",
     ["Why, how, by whom collected", "What it represents, where not to use it",
      "Licence, DOI, known issues ('wind' is airspeed, body-frame velocities)"],
     "T2", ["DATASHEET.md"], ["One page"]),
    ("D3", "MODEL_CARD.md", "uiml", "docs", "should",
     "Professional documentation of the ML part.",
     ["Purpose, data, features", "R2 and MAE +- std, comparison with linear regression, grouped "
      "test", "Limits: R6 shift, Matrice 100 only, association not causation"],
     "C1", ["docs/MODEL_CARD.md"], ["Half a page"]),
    ("D1", "README", "all", "docs", "critical path",
     "Assignment item 4: description, data, setup, contributions.",
     ["Title, live link, screenshot", "Project and research question (CRISP-DM phases)",
      "Data: source, DOI, licence, why raw data is not in the repo", "Setup",
      "Architecture (short)", "Charts table: chart, sub-question, interaction, author",
      "Requirement traceability: assignment item -> where -> evidence", "Contributions table",
      "Quality: data tests, RUSTIC, user test"],
     "E4", ["README.md"], ["A stranger can run the app from the README alone"]),
    ("R1", "One-page report", "uiml", "docs", "critical path",
     "Assignment item 6.",
     ["Dataset and context", "Goals (research question)",
      "Techniques (10 charts + 2 ML, one line each)", "Key findings with numbers",
      "GitHub and live links"],
     "D1", ["report.pdf"], ["One page, English, links work"]),
    ("P1", "Presentation slides", "all", "docs", "must",
     "Assignment item 5; graded individually.",
     ["Opening story -> research question", "Data and cleaning",
      "Each member: own section, 2-3 slides", "ML (K-means + Random Forest regression)",
      "Evaluation: RUSTIC + user test", "Closing: 3 findings + limits",
      "Backup screenshots for the live demo"],
     "E4", ["Slides"], ["Everyone's slides ready"]),
    ("S1", "v1.0.0 release + submission form", "platform", "deploy", "critical path",
     "The submitted version stays fixed.",
     ["Tag v1.0.0 + GitHub Release with short notes", "Form: release link, live link, report"],
     "D1, R1", ["Release", "Form"], ["Form sent by 18:00 Sunday"]),
    ("P2", "Rehearsal", "all", "docs", "must",
     "Individual grading; everyone presents their part comfortably.",
     ["One timed full run",
      "Likely questions: why 3D, how were the phases validated, why not a calendar, how were "
      "outliers found, why is RF better than linear (answers in decisions.md)",
      "Plan B with screenshots if the live demo fails"],
     "P1", ["-"], ["Everyone presented within time"]),
]
# fmt: on


def gh(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=check)


def body(t: tuple) -> str:
    tid, _, role, _, _, why, steps, dep, out, done = t
    owner = f"Section owner ({SECTION[role[-1]]})" if role.startswith("section:") else role
    lines = [f"**Task {tid}** · owner: {owner}", "", "### Why", why, "", "### Steps"]
    lines += [f"- [ ] {s}" for s in steps]
    lines += ["", "### Depends on", dep, "", "### Produces"] + [f"- {o}" for o in out]
    lines += ["", "### Done when"] + [f"- [ ] {d}" for d in done]
    return "\n".join(lines)


def labels_and_assignees(t: tuple) -> tuple[list[str], list[str]]:
    role, kind, prio = t[2], t[3], t[4]
    if role.startswith("section:"):
        r = SECTION_ROLE[role[-1]]
        return [ROLE_LABEL[r], kind, prio], [GH_USER[r]]
    if role == "all":
        return ["role: all", kind, prio], list(GH_USER.values())
    return [ROLE_LABEL[role], kind, prio], [GH_USER[role]]


def gh_json(*args: str):
    return json.loads(gh(*args).stdout)


class Board:
    """Adds issues to a GitHub Project (v2) and sets Status, Day and Estimate (h)."""

    def __init__(self, number: int, owner: str) -> None:
        self.n, self.owner = str(number), owner
        self.pid = gh_json("project", "view", self.n, "--owner", owner, "--format", "json")["id"]
        fields = self._fields()
        if "Day" not in fields:
            gh(
                "project",
                "field-create",
                self.n,
                "--owner",
                owner,
                "--name",
                "Day",
                "--data-type",
                "SINGLE_SELECT",
                "--single-select-options",
                ",".join(DAYS),
            )
        if "Estimate (h)" not in fields:
            gh(
                "project",
                "field-create",
                self.n,
                "--owner",
                owner,
                "--name",
                "Estimate (h)",
                "--data-type",
                "NUMBER",
            )
        self.fields = self._fields()  # fmt: skip

    def _fields(self) -> dict:
        data = gh_json("project", "field-list", self.n, "--owner", self.owner, "--format", "json")
        return {f["name"]: f for f in data["fields"]}

    def _option(self, field: str, name: str) -> str | None:
        for o in self.fields.get(field, {}).get("options", []):
            if o["name"].lower() == name.lower():
                return o["id"]
        return None

    def put(self, url: str, tid: str) -> None:
        item = gh_json("project", "item-add", self.n, "--owner", self.owner, "--url", url,
                       "--format", "json")["id"]  # fmt: skip
        base = ["project", "item-edit", "--id", item, "--project-id", self.pid]
        day, hours = PLAN[tid]
        status = "In Progress" if tid == "T0" else "Todo"
        for field, opt in (("Status", status), ("Day", day)):
            oid = self._option(field, opt)
            if oid:
                gh(*base, "--field-id", self.fields[field]["id"], "--single-select-option-id", oid)
        gh(*base, "--field-id", self.fields["Estimate (h)"]["id"], "--number", str(hours))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print, create nothing")
    ap.add_argument("--no-assign", action="store_true", help="create issues unassigned")
    ap.add_argument("--project", type=int, help="GitHub Project number to add the issues to")
    ap.add_argument(
        "--adopt",
        action="append",
        default=[],
        metavar="TASK=NUMBER",
        help="use an existing issue for a task instead of creating one, e.g. T2=1",
    )
    a = ap.parse_args()

    if a.dry_run:
        for t in TASKS:
            lab, asg = labels_and_assignees(t)
            print(f"[{t[0]}] {t[1]}  labels={lab} assignees={asg} plan={PLAN[t[0]]}")
        print(f"\n{len(TASKS)} issues, {len(LABELS)} labels, milestone '{MILESTONE}'")
        return

    if any(v.endswith("_USERNAME") for v in GH_USER.values()) and not a.no_assign:
        sys.exit("Fill in GH_USER at the top of the script (or run with --no-assign).")

    for name, (color, desc) in LABELS.items():
        gh("label", "create", name, "--color", color, "--description", desc, "--force")
    print(f"labels: {len(LABELS)} ok")

    repo = gh("repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner").stdout.strip()
    existing_ms = json.loads(gh("api", f"repos/{repo}/milestones?state=all").stdout)
    if not any(m["title"] == MILESTONE for m in existing_ms):
        gh(
            "api",
            f"repos/{repo}/milestones",
            "-f",
            f"title={MILESTONE}",
            "-f",
            f"due_on={MILESTONE_DUE}",
        )
    print("milestone ok")

    existing = {
        i["title"]: i["url"]
        for i in gh_json("issue", "list", "--state", "all", "--limit", "300", "--json", "title,url")
    }

    board = None
    if a.project:
        owner = repo.split("/")[0]
        board = Board(a.project, owner)
        print(f"project #{a.project} ok (fields: {', '.join(board.fields)})")

    adopt = dict(x.split("=", 1) for x in a.adopt)

    for t in TASKS:
        title = f"[{t[0]}] {t[1]}"
        if t[0] in adopt and title not in existing:
            num = adopt[t[0]]
            lab, asg = labels_and_assignees(t)
            args = ["issue", "edit", num, "--title", title, "--milestone", MILESTONE]
            for lb in lab:
                args += ["--add-label", lb]
            if not a.no_assign:
                for u in asg:
                    args += ["--add-assignee", u]
            r = gh(*args, check=False)
            if r.returncode != 0:
                sys.exit(f"failed to adopt #{num} for {t[0]}: {r.stderr}")
            gh("issue", "comment", num, "--body", "Plan for this task:\n\n" + body(t))
            url = gh("issue", "view", num, "--json", "url", "-q", ".url").stdout.strip()
            existing[title] = url
            print(f"adopt {title}  {url}")
            if board:
                board.put(url, t[0])
            continue
        if title in existing:
            print(f"skip  {title}")
            if board:
                board.put(existing[title], t[0])
            continue
        lab, asg = labels_and_assignees(t)
        args = ["issue", "create", "--title", title, "--body", body(t), "--milestone", MILESTONE]
        for lb in lab:
            args += ["--label", lb]
        base = list(args)
        if not a.no_assign:
            for u in asg:
                args += ["--assignee", u]
        r = gh(*args, check=False)
        if r.returncode != 0 and not a.no_assign:
            print(f"  warn: could not assign {asg} ({r.stderr.strip()}); creating unassigned")
            r = gh(*base, check=False)
        if r.returncode != 0:
            sys.exit(f"failed on {title}: {r.stderr}")
        url = r.stdout.strip().splitlines()[-1]
        print(f"ok    {title}  {url}")
        if board:
            board.put(url, t[0])


if __name__ == "__main__":
    main()
