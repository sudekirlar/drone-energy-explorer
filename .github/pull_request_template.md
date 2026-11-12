## What changed?
<!-- 1–3 sentences -->

Closes #

## Why?
<!-- Which sub-question or task does this serve? -->

## Screenshot
<!-- Required for any change visible in the app (reviewers may not run it immediately) -->

## Checklist
- [ ] Branch is one issue only; commit messages follow CONTRIBUTING.md
- [ ] `pytest` passes and `ruff` is clean locally (CI is green)
- [ ] No `import streamlit` in `src/data`, `src/charts`, `src/ml`
- [ ] Column names and units match `src/data/schema.py`

### For a chart (delete if not a chart)
- [ ] Title states the message, not just the variables (Guideline #7)
- [ ] Axis titles with units; legend when there is more than one series
- [ ] One-line "how to read" and a Finding box
- [ ] At least one meaningful interaction (Yi et al. type: …)
- [ ] Colours only from `src/theme.py`; no rainbow, pie or dual axis
- [ ] Readable under colour-blindness emulation
- [ ] Widget keys are unique and prefixed with the chart scope
- [ ] `docs/decisions.md` updated if a design decision was made
