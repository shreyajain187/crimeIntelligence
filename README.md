# OmniWatch — Crime Intelligence & Predictive Safety Dashboard

A full-stack ML project that turns nine years of real Karnataka Police FIR
(First Information Report) records into geographic intelligence, predictive
analytics, and explainable model output. Built as a college ML/full-stack
project — functional, honestly evaluated, and not over-engineered into a
production system.

## 1. Purpose

OmniWatch answers five questions from real police data, and only from real
police data:

- Where does crime concentrate geographically? (hotspot detection)
- What type of crime is most likely, given a place and time? (prediction)
- How risky is a given district, and why? (transparent risk scoring)
- How is incident volume trending, and what does the near future look like?
  (forecasting)
- Why did the model predict what it predicted? (SHAP explainability)

Every number in the dashboard — every statistic, prediction, metric, SHAP
value, and forecast — is computed from the actual dataset and actual trained
models. Nothing is hardcoded or fabricated. Where the data can't support a
claim (e.g. exact incident coordinates for 70% of records), the UI says so
explicitly rather than inventing a value.

## 2. Dataset

**"FIR DETAILS (KARNATAKA POLICE)"** —
https://www.kaggle.com/datasets/vanshangaria/fir-details-karnataka-police

- 1,674,734 real First Information Report records
- Karnataka Police, 41 districts, 2016–2024
- Columns include: District, Police Station (UnitName), crime category
  (CrimeGroup_Name / CrimeHead_Name), date (FIR_YEAR/MONTH/Day), victim and
  accused demographics, and Latitude/Longitude for a subset of records.

### Why this dataset, and what it does *not* give us

This project originally targeted a dataset with dense per-incident GPS
coordinates and hour-level timestamps (the kind of thing city police
open-data portals in the US publish, e.g. Chicago/LA). No such dataset for
an Indian city was reachable during development:

- NCRB's own published data is state/district *aggregate* yearly statistics
  with no per-incident geometry at all.
- The Kaggle datasets that do exist at incident granularity for India vary
  widely in what location detail they include.

The Karnataka FIR dataset used here is a genuine middle ground: real,
incident-level, with day-level dates and real administrative geography for
**100%** of records, and real GPS coordinates for **~32%** of records after
cleaning (483,069 of 1,508,042 cleaned rows). This shaped several design
decisions documented throughout this README (hotspot detection operates only
on the geocoded subset; the classifier predicts a *category* rather than
super fine-grained subtype; forecasting is day-level, not hour-level).

### License / redistribution

Review the current license terms on the Kaggle dataset page before
redistributing the raw file. This repo's `.gitignore` excludes the raw CSV
from version control for that reason.

## 3. Architecture

```text
Karnataka FIR CSV (raw)
        ↓
Dataset Adapter (ml/adapters/karnataka_fir_adapter.py)
        ↓
Validation + Cleaning (ml/cleaning.py) → documented CleaningSummary
        ↓
Feature Engineering (ml/features.py)
        ↓
 ┌──────────────┬─────────────────┬────────────────┐
 ↓              ↓                 ↓
DBSCAN        XGBoost          XGBoost
Hotspots      Classifier       Forecaster
(ml/hotspots) (ml/classifier)  (ml/forecast)
 ↓              ↓                 ↓
Hotspot       SHAP             Daily volume
summary       Explanations     + uncertainty
 └──────────────┴─────────────────┘
                 ↓
         District Risk Scores (ml/risk_score.py)
                 ↓
        scripts/run_pipeline.py (orchestrates all of the above, idempotent)
                 ↓
        scripts/load_database.py → SQLite (data/processed/omniwatch.db)
                 ↓
              FastAPI (backend/app)
                 ↓
           React Dashboard (frontend/)
```

## 4. Tech stack

**Data/ML:** Python, Pandas, NumPy, scikit-learn, XGBoost, SHAP.
cuDF/cuML/GPU SHAP are used automatically when RAPIDS + CUDA are detected
(see `ml/compute_backend.py`); the project runs entirely on CPU otherwise.

**Backend:** FastAPI, Pydantic, SQLAlchemy, SQLite (PostgreSQL+PostGIS
migration path documented below).

**Frontend:** React (Vite), Tailwind CSS v4, Recharts, React-Leaflet.

## 5. Project structure

```text
omniwatch/
├── backend/app/         FastAPI app: api/, core/, db/, schemas/
├── frontend/             React (Vite) dashboard
├── ml/                   Pipeline modules: adapters, cleaning, features,
│                         hotspots, classifier, explain, forecast, risk_score
├── scripts/              download_dataset.py, run_pipeline.py, load_database.py
├── data/raw/             Raw CSV (gitignored)
├── data/processed/       Cleaned parquet, hotspots.csv, risk_scores.csv,
│                         forecast_overall.json, omniwatch.db (all gitignored)
├── artifacts/models/     Trained classifier (pkl), metrics, SHAP importance
├── tests/                pytest suite for cleaning/features/hotspots/
│                         forecast/API
├── docker-compose.yml    Optional PostgreSQL+PostGIS service
└── .env.example
```

## 6. Setup

```bash
1. activate venv
python -m venv .venv
.venv\Sctipts\activate
2. Python environment
pip install -r requirements.txt

3. Get the dataset (see scripts/download_dataset.py for full instructions -
python scripts/download_dataset.py --from-zip /path/to/downloaded/archive.zip

4. Run the full ML pipeline (idempotent - safe to re-run; skips stages
#    whose output already exists unless --force is passed)
python scripts/run_pipeline.py

5. Load processed data + artifacts into SQLite
python scripts/load_database.py

6. Start the backend
uvicorn backend.app.main:app --reload --port 8000

7. Start the frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Environment variables (see `.env.example`): `KAGGLE_USERNAME`, `KAGGLE_KEY`
(optional, only for automated Kaggle download), `DATABASE_URL` (optional,
defaults to local SQLite), `VITE_API_BASE_URL` (frontend → backend URL).

## 7. Data cleaning methodology

Implemented in `ml/cleaning.py`, producing a `CleaningSummary` (surfaced live
in the dashboard's System page, not just in this doc):

- **Duplicates**: exact matches across timestamp/crime_type/district/
  station/coordinates/victim/accused counts are removed (166,692 of
  1,674,734 raw rows — the dataset has a meaningful rate of duplicate FIR
  entries).
- **Invalid dates**: reconstructed from FIR_YEAR/MONTH/Day; unparseable
  combinations become NaT and are dropped (0 in this dataset — dates were
  clean after reconstruction).
- **Out-of-range years**: dropped if outside the dataset's documented
  2016–2024 coverage.
- **Invalid coordinates**: checked against Karnataka's real geographic
  bounding box (10.5–19.5°N, 73.5–79.0°E, with a small buffer). Invalid
  coordinates are **not** used to drop the row — they're cleared to null
  (never fabricated or clamped to a fake value), and the record remains
  usable for non-spatial analysis. 20,291 rows had invalid coordinates.
- **Invalid categories**: blank/null crime_type rows dropped.

Result: 1,674,734 → 1,508,042 rows. 463 distinct crime types (bucketed into
16 crime_group classes for modelling), 41 districts, 1,054 stations,
483,069 rows (32%) with usable coordinates.

## 8. Feature engineering (`ml/features.py`)

- **Temporal**: year, month, day, day_of_week, is_weekend, season (mapped
  to India's actual seasonal calendar: winter/summer/monsoon/post-monsoon).
- **Historical frequency**: for each row, a *trailing 90-day* count of prior
  incidents at the same station, computed via a shifted rolling window so a
  row can never see its own or future incidents (verified in
  `tests/test_features.py::test_historical_frequency_has_no_leakage`).
- **Station total incidents**: an all-time station-level volume attribute,
  used only as a station-identity proxy for modelling (see leakage notes
  below on why raw station identity itself is excluded from the classifier).

## 9. Hotspot detection (`ml/hotspots.py`)

DBSCAN over the 483,069 geocoded records, using proper haversine distance
(not naive Euclidean degrees) with `eps=0.75km`, `min_samples=15`.
Cluster `-1` (noise) is excluded from hotspot summaries. Result: **2,434
real geographic hotspot clusters**, concentrated heavily around Bengaluru
City/District as expected, with smaller clusters around other major cities
(Mangaluru, Hubballi-Dharwad, Mysuru, Kalaburagi, Belagavi, etc.).

GPU path: when RAPIDS/cuML is available, uses cuML DBSCAN with a local
planar projection (cuML's DBSCAN doesn't expose a haversine metric); falls
back to sklearn DBSCAN with `metric="haversine"` otherwise. Verified not to
crash without CUDA/RAPIDS (this repo's dev environment has neither).

## 10. Crime-type prediction (`ml/classifier.py`)

**Target**: `crime_group` — the 463 raw crime_type values bucketed into the
top 15 most frequent groups + "OTHER" (16 classes total).

**Features used**: year, month, day, day_of_week, is_weekend,
historical_frequency, station_total_incidents, victim_count, district,
season.

**Leakage avoidance:**
- `crime_type` is never a feature (crime_group is derived directly from it —
  using it would make the task circular).
- `accused_count`, `arrested_count`, `chargesheeted_count`, `conviction_count`
  are excluded — these are case-outcome fields only known *after*
  investigation/adjudication, not at prediction time.
- Raw `station` (1,054 distinct values) is deliberately **not** used as a
  categorical split feature — on the single-core CPU this was developed on,
  splitting on a 1000+-level categorical was prohibitively slow, and its
  signal is already captured numerically via `historical_frequency` and
  `station_total_incidents`.

**Split**: temporal, not random — train on 2016–2022, test on 2023–2024, so
evaluation reflects genuinely future incidents.

**Class imbalance — an honest finding, not a tuned-away one**: balanced
inverse-frequency sample weighting was tried and **reduced** overall
accuracy *below* the trivial majority-class baseline (18.0% vs. a 20.3%
"always guess OTHER" baseline). Unweighted training is used instead, which
beats the baseline (**29.5% accuracy**) while macro-F1 remains modest
(0.137) — reflecting real difficulty on the imbalanced minority classes.
Both weighted and unweighted results are documented here rather than only
reporting whichever number looked better.

**Real evaluation on the 2023–2024 held-out set:**

| Metric | Value |
|---|---|
| Accuracy | 0.295 |
| Precision (weighted) | 0.271 |
| Recall (weighted) | 0.295 |
| F1 (weighted) | 0.230 |
| F1 (macro) | 0.137 |
| Majority-class baseline | 0.203 |

Full confusion matrix and per-class precision/recall/F1 are in
`artifacts/models/classifier_metrics.json` and rendered in the dashboard's
Model Insights page.

**Honest limitation**: predicting fine-grained crime *type* from only
when/where an FIR was filed is a genuinely hard, weak-signal problem — most
of what determines a crime's category lives in case-specific facts this
dataset doesn't capture pre-investigation. The model is presented as
decision support describing historical patterns, never as a confident
forecast of a specific future event.

## 11. SHAP explainability (`ml/explain.py`)

`shap.TreeExplainer` (CPU) by default; attempts `shap.explainers.GPUTree`
when a GPU backend is active, falling back cleanly otherwise. Provides:

- **Global feature importance**: mean(|SHAP value|) across classes, sampled
  from the 2023–2024 test set. Top drivers: `district` (0.596),
  `station_total_incidents` (0.356), `year` (0.210), `historical_frequency`
  (0.122) — i.e., *where* dominates *when* for this model.
- **Per-prediction explanation**: SHAP values for the specific predicted
  class, exposed via `POST /api/explain`.

Language used throughout the API and UI: "features associated with the
model's prediction," never a causal claim.

## 12. Forecasting (`ml/forecast.py`)

**XGBoost, not Prophet** — a deliberate choice. Prophet requires a compiled
Stan (cmdstanpy) backend, which is a common source of environment-specific
breakage (native compilation, large first-run downloads) — exactly the kind
of unreliability this project is trying to avoid for a "must work on an
ordinary laptop" requirement. XGBoost has no such dependency.

**Approach**: daily total incident counts, modelled with lag features
(t-1, t-7, t-14, t-28), rolling mean/std (7d, 28d), and calendar features.
Validated on the trailing 60 real days before forecasting forward.

**Real validation performance**: MAE 47.1, RMSE 59.3 incidents/day (against
a typical daily volume in the several-hundred range) — presented as-is in
the Forecast page.

**Uncertainty band**: ±1.96×RMSE around the point forecast — an
approximation based on residual spread, explicitly documented as such
rather than a formal prediction interval.

Only the overall (all-Karnataka) forecast is precomputed by the pipeline;
`GET /api/forecast?district=...` correctly returns a 501 rather than
silently training a new model per API request.

## 13. Risk score (`ml/risk_score.py`)

Transparent 0–100 composite score per district:

```text
risk_score = 100 × ( 0.40 × norm(incident_density)
                    + 0.30 × norm(recent_90d_activity_ratio)
                    + 0.15 × norm(hotspot_membership_share)
                    + 0.15 × norm(monthly_trend_slope) )
```

All four components are real, measurable quantities from the cleaned
dataset (station-normalized density, a genuine recent-vs-historical 90-day
ratio, the real share of a district's geocoded incidents falling inside a
DBSCAN hotspot, and an actual linear trend slope over monthly incident
counts), each min-max normalized across the 41 observed districts — never
against an arbitrary fixed scale. Interpretation bands: 0–30 Low, 31–60
Moderate, 61–80 High, 81–100 Very High. Presented as a descriptive summary
of historical patterns, not a probability or forecast.

## 14. Database

Runs on **SQLite** by default (zero setup). ORM models
(`backend/app/db/models.py`) are written to map directly onto PostgreSQL +
PostGIS:

- `crimes.latitude`/`longitude` (two floats here) → a single
  `geometry(Point, 4326)` column with a GiST index in Postgres.
- All other tables map 1:1 with no changes.

To migrate: `docker compose up -d` (starts `postgis/postgis:16-3.4`), set
`DATABASE_URL=postgresql://omniwatch:omniwatch@localhost:5432/omniwatch`,
re-run `python scripts/load_database.py`. Equivalent PostGIS schema:

```sql
CREATE TABLE crimes (
  id SERIAL PRIMARY KEY,
  crime_id TEXT UNIQUE,
  timestamp TIMESTAMP,
  crime_type TEXT,
  crime_group TEXT,
  geom GEOMETRY(Point, 4326),
  has_coordinates BOOLEAN,
  location TEXT,
  district TEXT,
  station TEXT,
  victim_count INTEGER,
  cluster_id INTEGER
);
CREATE INDEX ix_crimes_geom ON crimes USING GIST (geom);
CREATE INDEX ix_crimes_district_timestamp ON crimes (district, timestamp);
```

## 15. API (`backend/app`)

| Endpoint | Description |
|---|---|
| `GET /api/health` | Liveness check |
| `GET /api/metadata` | Dataset provenance, cleaning summary, compute backend |
| `GET /api/stats` | Aggregate dashboard statistics |
| `GET /api/crimes` | Paginated, filterable, searchable record list |
| `GET /api/crimes/map` | Point-level records for the map (hard-capped at 20,000, coordinates only) |
| `GET /api/districts`, `/api/crime-groups` | Filter option lists |
| `GET /api/hotspots` | DBSCAN cluster summaries |
| `GET /api/risk-scores` | Per-district risk scores |
| `GET /api/model/metrics` | Classifier evaluation metrics |
| `GET /api/model/features` | Global SHAP feature importance |
| `GET /api/forecast` | Overall daily-volume forecast |
| `POST /api/predict` | Crime-type prediction for a district/date |
| `POST /api/explain` | SHAP explanation for a specific prediction |

All list endpoints are paginated or hard-capped — the multi-million-row
table is never sent to the frontend in full.

## 16. Frontend

React + Vite + Tailwind v4. Pages: Landing, Overview, Crime Map, Hotspots,
Predictions, Forecast, Model Insights, Data Explorer, System. Deliberately
designed as a GIS command-console (charcoal background, restrained
burnt-orange accent, off-white type, Space Grotesk/IBM Plex typography,
hairline borders instead of shadows/rounded cards) rather than a generic
SaaS-dashboard template, per the project's UI requirements.

**Verification note**: this sandbox has no headless-browser access (network
egress is allowlisted and blocks Playwright/Chromium downloads), so the UI
could not be visually screenshotted during development. `npm run build`
completes cleanly and the dev server starts without runtime errors, and
every API call the frontend makes was independently verified against the
live backend via curl — but a manual visual pass in a real browser is
recommended before considering the frontend fully verified.

## 17. GPU/CPU fallback

`ml/compute_backend.py` detects CUDA (via `torch.cuda` or `nvidia-smi`
presence) and RAPIDS (`cudf`/`cuml` importability) without ever raising if
absent. `active_backend` is `"gpu"` only when both CUDA and RAPIDS are
present; otherwise `"cpu"`. Hotspot detection, the XGBoost classifier, and
SHAP all check this and fall back automatically. This project's own
development/test environment has neither CUDA nor RAPIDS and runs entirely
on CPU (visible live on the dashboard's System page).

## 18. Testing

```bash
python -m pytest tests/ -v
```

21 tests covering: cleaning (duplicates, invalid dates, coordinate
bounding-box handling), feature engineering (temporal correctness, and
explicit no-leakage verification for historical_frequency), hotspot
detection (a synthetic dense cluster is correctly found and isolated points
correctly marked as noise), forecasting (output shape, non-negativity,
insufficient-history error handling), and the full FastAPI surface
(pagination, filtering, coordinate-only map endpoint, unknown-district
rejection) against an isolated temporary test database seeded with
clearly-synthetic fixture rows — never the real dataset, and never
conflated with what the running application actually serves.

## 19. Limitations

- **Coordinate coverage**: only ~32% of records have real geocoordinates;
  hotspot detection and the point map necessarily exclude the rest rather
  than fabricating a location.
- **Classifier accuracy is modest** (29.5%) — genuinely limited predictive
  signal in time/location alone for fine-grained crime type, documented
  rather than hidden.
- **Forecast uncertainty bands are approximate** (±1.96×RMSE), not a formal
  statistical prediction interval.
- **Filtered (per-district/category) forecasts are not precomputed** — the
  API returns 501 for these rather than training on-demand.
- **Single development machine had 1 CPU core** — classifier training takes
  ~5–6 minutes here; expect it to be substantially faster on a normal
  multi-core laptop.
- **No production deployment infrastructure** by design — this is a
  college project, not a production service.

## 20. Responsible AI considerations

- Predictions and risk scores are presented as descriptive statistical
  decision support, never as certainty about a specific individual, place,
  or future event — this disclaimer appears in the UI itself (Predictions
  page, Landing page), not just in this document.
- The dataset reflects *reported* crime, which is known to undercount many
  offence types differently across regions and demographics; district risk
  scores should be read as reflecting reporting and enforcement patterns,
  not an unmediated measure of "true" crime rates.
- No individual-level identifying information is used or exposed — the
  dataset and this application operate at station/district/date
  granularity, never naming or profiling specific people.
- SHAP explanations are described as "features associated with the model's
  prediction" throughout, deliberately avoiding causal language.
