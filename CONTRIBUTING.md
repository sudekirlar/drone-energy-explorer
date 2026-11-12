# Contributing

How the three of us work on this repo. Short rules, applied every time, so the history reads as one
team's work and every member's contribution is visible.

| Role | Member | Owns | Section (3 charts) |
|---|---|---|---|
| Platform | Sude | repo and standards, data contract (`schema.py`, `loader.py`), flight phases, deployment, merge order | Energy & Experimental Conditions: Sankey, treemap, payload × speed heatmap + RF view |
| Data | İlayda | sample tables, cleaning and flight summaries (`preprocess.py`), data tests, Overview & Data Quality | Flight & Temporal Analysis: route map, 3D Space-Time Cube, phase-annotated timeline (+ links between them) |
| UI & ML | Pelin | app frame (`app.py`, menu, sidebar filters), `theme.py`, K-means, Random Forest regression, Model Card | Multivariate Analysis & ML: parallel coordinates, SPLOM, violin + box, flight × time heatmap |

Ten charts in total; the full list, sub-questions and decisions are in the chart guide and in
`docs/decisions.md`.

---

## 1. One-time setup (each member)

```bash
# 1. Commits must use the SAME e-mail as your GitHub account,
#    otherwise they are not linked to your profile and you are invisible in Insights → Contributors.
git config --global user.name  "Your Name"
git config --global user.email "the-email-on-your-github-account"

# 2. Clone and use the shared commit template
git clone <repo-url>
cd <repo>
git config commit.template .gitmessage

# 3. Python 3.13 environment (everyone on the same version)
python -m venv .venv
.venv\Scripts\activate              # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
pre-commit install                  # ruff + safety checks run on every commit

# 4. Check
pytest                              # should pass
streamlit run app.py                # opens the app in the browser
```

PyCharm: *Settings → Project → Python Interpreter → Add Interpreter → Local → Virtualenv*, location
`<repo>/.venv`, base Python 3.13. The PyCharm terminal then activates `.venv` by itself.

Check step 1 with `git log -1 --format='%an <%ae>'` after your first commit.

Raw data goes into `data/raw/` (see the README there). It is ignored by git.

---

## 2. Branches

`main` is protected: no direct pushes, every change arrives through a pull request with one approval
and a green CI check.

Branch name: `<type>/<issue-number>-<short-slug>`

```
feat/13-route-map
feat/16-sankey-energy-budget
data/1-cleaning-flight-summaries
fix/22-flight-heatmap-sort-order
docs/32-readme
```

Keep a branch to one issue. Small PRs get reviewed fast; a 1,000-line PR on Saturday night will not.

---

## 3. Commit messages

Format ([Conventional Commits](https://www.conventionalcommits.org)), written in **English**:

```
<type>(<scope>): <subject>

<body: why this change, what it does — optional, wrap at 72>

Refs #<issue>
Co-authored-by: Name <github-email>
```

**Subject:** imperative mood ("add", not "added"), lowercase, no full stop, ≤ 72 characters.

### Types
| Type | Use for |
|---|---|
| `feat` | a new chart, control, section or model |
| `fix` | a bug fix |
| `data` | preprocessing rules, cleaning, derived variables, processed files |
| `ml` | model training, evaluation, metrics |
| `style` | visual consistency: titles, palette, labels, layout (no logic change) |
| `refactor` | code restructuring without behaviour change |
| `docs` | README, report, decisions, comments, this file |
| `test` | tests |
| `chore` | setup, dependencies, config, CI |

### Scopes
| Area | Scopes |
|---|---|
| Shared / platform | `repo`, `deps`, `ci`, `schema`, `loader`, `phases`, `deploy`, `readme`, `report`, `decisions` |
| Data | `prep`, `sample`, `tests`, `quality` |
| UI & ML | `app`, `theme`, `filters`, `kmeans`, `regressor` |
| Flight & Temporal charts | `route-map`, `stc`, `timeline`, `links` |
| Energy & Experimental Conditions charts | `sankey`, `treemap`, `payload-heatmap` |
| Multivariate & ML charts | `pcp`, `splom`, `violin`, `flight-heatmap` |

### Examples
```
feat(route-map): colour flight track by instantaneous power
data(prep): correct four start-time typos and keep raw values
data(phases): merge segments shorter than 2 s into the previous phase
feat(sankey): let user group energy by altitude, speed, payload or route
ml(regressor): report R² and MAE as mean ± std over 5 seeds
feat(splom): highlight selected flights in every panel
style(theme): use one tone family per payload class
fix(filters): keep colour per payload stable when the filter changes
docs(readme): add contributions table and dataset citation
```

### Pair work
If two of you wrote it together, the committer adds:
```
Co-authored-by: Teammate Name <teammate-github-email>
```
GitHub then credits both people on that commit.

### Don't
- `update`, `fix stuff`, `final`, `final2`, `asdf`
- one commit containing three unrelated changes
- committing anything from `data/raw/` (ignored; the pre-commit hook also blocks files > 20 MB)

---

## 4. Daily workflow

Every planned task already has an issue, assigned to its owner and placed on the project board
(Day and Estimate filled in). **Do not open a new issue for a planned task.** Open one only for
something the plan does not cover: a bug, a question that blocks you, or an idea (label `later`).

1. On the board, filter by your name, pick the task for today and move its card to **In Progress**.
2. Create a branch named after the issue (below). The issue page's *Development → Create a branch*
   button does the same.
3. Commit in small steps with `Refs #<issue>` in the footer.
4. Push, open a PR (`Refs #n` or `Closes #n`, see section 5), request the reviewer and move the
   card to **In Review**.
5. After approval, merge with "Create a merge commit". `Closes #n` closes the issue and the card
   moves to **Done** by itself.

```bash
git switch main && git pull                 # start from the latest main
git switch -c feat/13-route-map             # one branch per issue
# ... work, commit in small steps ...
git pull origin main                        # bring in teammates' merged work, fix conflicts locally
git push -u origin feat/13-route-map
# open a PR on GitHub
```

Daily status message (same time every day, team chat):
```
Yesterday: #16 Sankey three levels done (PR open)
Today: percent mode + finding text
Blocked: phase_energy has no "sloped cruise" rows, asked Sude
```

---

## 5. Pull requests

- **Title** uses the same format as a commit subject: `feat(route-map): add power-coloured route map`.
- **Description** follows the PR template and links the task issue:
  - `Refs #13` when the PR is one step of the task (the issue stays open),
  - `Closes #13` in the PR that finishes the task (the issue closes on merge and its card moves
    to Done).
- **Reviewer:** CODEOWNERS requests the file owner automatically. For section PRs we rotate:
  - Sude's PRs → İlayda
  - İlayda's PRs → Pelin
  - Pelin's PRs → Sude
  - If the assigned reviewer is busy for more than 6 hours, anyone may review.
- **Merge method: "Create a merge commit".** Squash and rebase are disabled, so every commit keeps
  its author.
- The branch is deleted automatically after merging.
- Merge order is Platform's call when several PRs touch shared files.

### Reviewing
Reviews are part of your visible contribution. Leave at least one concrete comment, positive or
critical. Check:
1. The app runs locally on your machine.
2. The PR template checklist.
3. CI is green.

Use **Request changes** when something on the checklist fails, **Approve** when it passes.

---

## 6. Code rules

- **Layers.** `src/charts/<chart>.py` exposes `build_<chart>(df, ...) -> go.Figure`. `src/data` and
  `src/ml` are plain Python. None of these three import Streamlit (`tests/test_architecture.py`
  enforces it). UI code (widgets, `st.plotly_chart`, text, `@st.cache_data`, `@st.fragment`) lives in
  `app.py` and `src/sections/<section>.py`.
- **Sections, not tabs.** The top menu renders only the selected section; `st.tabs` would run all of
  them on every rerun. Every chart card is an `@st.fragment`.
- **Widget keys:** every widget gets a unique `key` prefixed with its chart scope:
  `key="sankey_group_by"`. Two widgets with the same label and no key crash the app.
- **Colours** only from `src/theme.py`. No hard-coded hex values in chart files.
- **Data** is read through `src/data/loader.py`. Column names, types and units follow
  `src/data/schema.py`: lowercase, unit at the end (`power_w`, `energy_wh`, `alt_rel_m`). Never
  read files inside a chart. How charts, sections and shared state plug together:
  `docs/interfaces.md`.
- **Contract changes** go through a PR labelled `contract`, approved by Platform and the role that
  produces the table; bump `SCHEMA_VERSION`.
- **Ownership.** Change someone else's file only through an issue or after asking them.
- **Notebooks** (`notebooks/`) are for exploration. Anything the app needs must live in `src/`.
- **Decisions** that affect the team get three lines in `docs/decisions.md`: decision, alternative, why.

---

## 7. For AI assistants

Paste this block into your AI chat so generated code and commits follow the same rules:

```text
Project rules (CEN445 Streamlit dashboard; Python 3.13, streamlit 1.67, plotly 7.1, pandas 3.1,
scikit-learn 1.9):
- Layers: src/charts/<chart>.py exposes build_<chart>(df, ...) -> plotly Figure. src/data, src/ml and
  src/charts must NOT import streamlit. UI code (widgets, st.cache_data, st.fragment) lives in app.py
  and src/sections/<section>.py, each with render(...). app.py only wires the menu and sidebar filters.
- Sections are switched with st.segmented_control, not st.tabs. Each chart card is an @st.fragment.
- Data comes from src/data/loader.py. Column names, types and units follow src/data/schema.py:
  lowercase with the unit at the end (power_w, energy_wh, wh_per_km, alt_rel_m, speed_mps).
  Never read files inside chart code. Interfaces (chart signature, section render(tables),
  shared session_state keys, ml_metrics.json): docs/interfaces.md.
- Colours only from src/theme.py. No rainbow/jet, no pie charts, no dual y-axes, no 3D except the
  Space-Time Cube.
- Every figure: message-style title, axis titles with units, legend when >1 series, hover with units.
- Every Streamlit widget gets a unique key prefixed with the chart scope, e.g. key="pcp_k".
- pandas 3: copy-on-write is always on; never use chained assignment (df[a][b] = x), use df.loc.
- Commit messages: Conventional Commits in English, "<type>(<scope>): <imperative subject>" (≤72).
  Types: feat, fix, data, ml, style, refactor, docs, test, chore. Footer "Refs #<issue>".
- ML: one row per flight; never split telemetry rows randomly between train and test.
  K-means on five outcome measures; Random Forest REGRESSION of cruise power from payload, speed,
  altitude, compared with linear regression. Flight phases are estimated (rule-based), never an
  ML target.
- The 'wind_speed' column is airspeed from the anemometer, not wind: label it "airspeed
  (anemometer)" and keep it out of multivariate charts and models.
```
