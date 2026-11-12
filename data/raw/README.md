# data/raw (not in git)

Put the original CMU files here. Everything in this folder except this README is ignored by git:
`flights.csv` is about 102 MB, above GitHub's 100 MB file limit.

**Source:** Rodrigues, T. A. et al. (2021). *Data Collected with Package Delivery Quadcopter Drone.*
Carnegie Mellon University, KiltHub. https://doi.org/10.1184/R1/12683453 (CC BY 4.0)

Expected layout after download and unzip:

```
data/raw/
├── parameters.csv        209 flights × 7 columns
├── flights.csv           257,896 rows × 28 columns
└── flights/              209 per-flight CSV files (optional, used by the audit)
```

Rules:
- This folder is **read-only**. Never open a raw CSV in Excel and save it; every change happens in
  `src/data/preprocess.py`.
- The app never reads this folder. It reads `data/processed/` (or `data/sample/` until the
  processed tables exist).
