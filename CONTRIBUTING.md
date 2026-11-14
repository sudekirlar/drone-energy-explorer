# How we worked

This file describes how our team of three worked on the repository: who owned which part, how we
named branches and commits, and how every change was reviewed before it reached `main`. We
followed the same rules for every change, so the history reads as one team's work and each
member's contribution is visible.

| Role | Member | Owns | Section (charts) |
|---|---|---|---|
| Platform | Sude | repo and standards, data contract (`schema.py`, `loader.py`), flight phases, deployment, merge order | Energy & Experimental Conditions: Sankey, treemap, payload × speed heatmap + RF view |
| Data | İlayda | sample tables, cleaning and flight summaries (`preprocess.py`), data tests, Overview & Data Quality | Flight & Temporal Analysis: route map, 3D Space-Time Cube, phase-annotated timeline (+ links between them) |
| UI & ML | Pelin | app frame (`app.py`, menu, sidebar filters), `theme.py`, K-means, Random Forest regression, Model Card | Comparison & Clusters: parallel coordinates, SPLOM, violin + box, flight × time heatmap |

The ten charts and the questions they answer are listed in the [README](README.md). The reasons
behind our main choices are in [docs/decisions.md](docs/decisions.md).

---

## 1. Setup

Every member set up the project in the same way, with the same Python version:

```bash
# Commits use the same e-mail as the GitHub account, so GitHub links them to the right person.
git config --global user.name  "Your Name"
git config --global user.email "the-email-on-your-github-account"

# Clone the repository and use the shared commit template.
git clone https://github.com/sudekirlar/drone-energy-explorer.git
cd drone-energy-explorer
git config commit.template .gitmessage

# Python 3.13 environment
python -m venv .venv
.venv\Scripts\activate              # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
pre-commit install                  # runs ruff and safety checks on every commit

# Check
pytest
streamlit run app.py
```

The raw data goes into `data/raw/` (see the README in that folder). Git ignores it.

---

## 2. Branches

`main` is protected. Nobody pushes to it directly: every change arrives through a pull request
with one approval and a passing CI check.

A branch is named `<type>/<issue-number>-<short-slug>`:

```
feat/13-route-map
feat/16-sankey-energy-budget
data/1-cleaning-flight-summaries
fix/22-flight-heatmap-sort-order
docs/32-readme
```

A branch serves one issue. Small pull requests are easier to review well.

---

## 3. Commit messages

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org) and are
written in English:

```
<type>(<scope>): <subject>

<body: why this change, what it does (optional, wrapped at 72 characters)>

Refs #<issue>
Co-authored-by: Name <github-email>
```

The subject is in the imperative mood ("add", not "added"), in lowercase, without a full stop,
and at most 72 characters long.

### Types
| Type | Use for |
|---|---|
| `feat` | a new chart, control, section or model |
| `fix` | a bug fix |
| `data` | preprocessing rules, cleaning, derived variables, processed files |
| `ml` | model training, evaluation, metrics |
| `style` | visual consistency: titles, palette, labels, layout (no logic change) |
| `refactor` | code restructuring without a change in behaviour |
| `docs` | README, report, decisions, comments, this file |
| `test` | tests |
| `chore` | setup, dependencies, configuration, CI |

### Scopes
| Area | Scopes |
|---|---|
| Shared / platform | `repo`, `deps`, `ci`, `schema`, `loader`, `phases`, `deploy`, `readme`, `report`, `decisions` |
| Data | `prep`, `sample`, `tests`, `quality` |
| UI & ML | `app`, `theme`, `filters`, `kmeans`, `regressor` |
| Flight & Temporal charts | `route-map`, `stc`, `timeline`, `links` |
| Energy & Experimental Conditions charts | `sankey`, `treemap`, `payload-heatmap` |
| Comparison & Clusters charts | `pcp`, `splom`, `violin`, `flight-heatmap` |

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
When two members wrote a change together, the commit names both of them with a trailer:
```
Co-authored-by: Teammate Name <teammate-github-email>
```
GitHub then credits both people for that commit.

### What we avoided
- We did not use vague messages such as "update", "fix stuff" or "final".
- We did not put unrelated changes into one commit.
- We did not commit anything from `data/raw/`. Git ignores the folder, and a pre-commit hook also
  blocks any file larger than 20 MB.

---

## 4. From task to merge

Every planned task had an issue on the project board, with an owner, a day and an estimate. We
opened new issues only for work the plan did not cover, such as a bug or a question that blocked
someone.

1. The owner moves the task's card to **In Progress**.
2. The owner creates a branch named after the issue.
3. The owner commits in small steps, with `Refs #<issue>` in each commit message.
4. The owner pushes the branch, opens a pull request, requests a reviewer and moves the card to
   **In Review**.
5. After approval, the pull request is merged with "Create a merge commit". `Closes #n` closes
   the issue, and the card moves to **Done**.

```bash
git switch main
git pull                                    # start from the latest main
git switch -c feat/13-route-map             # one branch per issue
# ... work, commit in small steps ...
git pull origin main                        # bring in teammates' merged work
git push -u origin feat/13-route-map
# open a pull request on GitHub
```

---

## 5. Pull requests

- The **title** has the same format as a commit subject: `feat(route-map): add power-coloured
  route map`.
- The **description** follows the pull request template and links the task's issue. It says
  `Refs #13` when the pull request is one step of the task, and `Closes #13` when it finishes the
  task.
- **Reviewer:** GitHub requests the owner of each changed file automatically (`CODEOWNERS`). For
  section pull requests we rotated: Sude's were reviewed by İlayda, İlayda's by Pelin, and Pelin's
  by Sude. When the assigned reviewer was busy for more than six hours, anyone could review.
- **Merge method:** "Create a merge commit". Squash and rebase merges are turned off, so every
  commit keeps its author.
- GitHub deletes a branch automatically after it is merged.
- When several pull requests changed shared files, Platform decided the order of merging.

### Reviewing
A review is part of a member's visible contribution, so every review leaves at least one concrete
comment. The reviewer checks three things:
1. The app runs on the reviewer's own computer.
2. Every item of the pull request checklist is met.
3. CI passes.

The reviewer chooses **Request changes** when an item fails, and **Approve** when all pass.

---

## 6. Code rules

- **Layers.** `src/charts/<chart>.py` exposes `build_<chart>(df, ...) -> go.Figure`. `src/data`
  and `src/ml` are plain Python. None of these three folders imports Streamlit, and
  `tests/test_architecture.py` checks this. UI code (widgets, `st.plotly_chart`, text,
  `@st.cache_data`, `@st.fragment`) lives in `app.py` and `src/sections/<section>.py`.
- **Sections, not tabs.** The top menu runs only the selected section, while `st.tabs` would run
  every section on every rerun. Every chart card is an `@st.fragment`.
- **Widget keys.** Every widget has a unique `key` that starts with its chart's scope, for example
  `key="sankey_group_by"`. Two widgets with the same label and no key crash the app.
- **Data.** Tables are read through `src/data/loader.py`. Column names, types and units follow
  `src/data/schema.py`: lowercase, with the unit at the end (`power_w`, `energy_wh`,
  `alt_rel_m`). Chart code never reads files. [docs/interfaces.md](docs/interfaces.md) describes
  how charts, sections and shared state fit together.
- **pandas 3.** Copy-on-write is always on, so we never use chained assignment
  (`df[a][b] = x`); we use `df.loc` instead.
- **Contract changes** go through a pull request labelled `contract`. Platform and the role that
  produces the table both approve it, and `SCHEMA_VERSION` goes up.
- **Ownership.** A member changes someone else's file only through an issue or after asking the
  owner.
- **Decisions** that affect the team get a short entry in [docs/decisions.md](docs/decisions.md):
  the decision, the alternative and the reason.

### Chart rules
- Colours come only from `src/theme.py`. There are no hard-coded colour values in chart files.
- We use no rainbow (jet) scales, no pie charts and no charts with two y-axes. The Space-Time Cube
  is the only 3D chart.
- Every chart has axis titles with units, a legend when it shows more than one series, and hover
  texts with units.
- A card's title names the chart, and the finding below it carries the message
  ([D18](docs/decisions.md)).
- The `wind_speed` column is the drone's airspeed from its anemometer, not the wind. It is labelled
  "airspeed (anemometer)" and kept out of the multivariate charts and the models
  ([D3](docs/decisions.md)).

### Machine-learning rules
- A model uses one row per flight. Telemetry rows are never split at random between training and
  testing, because rows of the same flight are almost copies of each other.
- K-means groups flights by their outcome measures. The Random Forest is a regression of cruise
  power on payload, speed and altitude, and it is compared with a linear regression
  ([D5](docs/decisions.md)).
- Flight phases are estimated with a rule ([D6](docs/decisions.md)). They are never the target of
  a model.
