# 🏀 NBA Analytics & Machine Learning Dashboard

![Python](https://img.shields.io/badge/Python-3.x-blue?style=flat&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red?style=flat&logo=streamlit)
![XGBoost](https://img.shields.io/badge/Machine%20Learning-XGBoost-orange)
![Scikit-Learn](https://img.shields.io/badge/Clustering-K--Means-green)

An end-to-end data science and machine learning platform focused on NBA player statistics, predictive awards forecasting, player playstyle clustering, and game outcome modeling.

> 🏗️ **v2 in progress**: the dashboard is being rebuilt as a FastAPI + Next.js application. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the design and roadmap.
>
> 📖 **Complete Documentation**: For an in-depth walkthrough of the data collection API endpoints, feature engineering math, era normalization rules, and machine learning architectures, see [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md).

---

## ✨ Features

- **Automated Data Pipeline**: Ingests, cleans, and processes raw multi-season NBA statistics via official API wrappers (`Base` and `Advanced` endpoints).
- **Machine Learning Models**:
  - **MVP Prediction**: XGBoost model using Leave-One-Season-Out Cross Validation (LOOCV), picking the actual MVP in **19 of 26 seasons (73.1%)**.
  - **All-Star Prediction**: Position-constrained, hand-weighted impact score that builds Eastern and Western conference rosters (6G / 6F / 3C).
  - **Player Archetype Clustering**: Standardized composite scores assign each player-season a playstyle, and 1D K-Means splits each into tiers (`Scorer`, `Playmaker`, `Rebounder`, `Defensive Player`) and performance tiers (`Elite`, `Very Good`, `Average`).
  - **Next Game Prediction**: XGBoost game outcome forecast from season-to-date overall, home and road win percentages (about as accurate as picking the team with the better record).
- **Interactive Streamlit Dashboard**: Full visual analytics web application featuring per-game player comparisons, franchise history, live MVP model prediction runners, and clustering visualizations.

---

## 📁 Repository Structure

```
NBAAnalyticsProject/
├── config/                 # Pipeline configuration files (config.yaml)
├── data/
│   ├── processed/          # Cleaned datasets (mvp_data.csv, all_stars_master.csv, etc.)
│   └── raw/                # Ingested raw player statistics (nba_player_stats.csv)
├── notebooks/              # Jupyter Notebooks for EDA and prototype testing
├── saved_models/           # Serialized machine learning models (.pkl)
├── src/
│   ├── pipeline.py         # Rebuilds every dataset and model in order
│   ├── paths.py / nba_reference.py / features.py  # Shared paths, reference data, feature helpers
│   ├── data_collection.py  # Script to ingest multi-season stats from NBA API
│   ├── data_pipeline/      # Data pipeline scripts (standings fetch, MVP dataset build)
│   └── models/             # Machine learning implementations (MVP, All-Star, Clustering, Next Game)
├── backend/                # v2 FastAPI service (app/, tests/, Dockerfile, openapi.json)
├── frontend/               # v2 Next.js web app (src/app routes, components, typed API client)
├── docker-compose.yml      # Runs the API and web app together
├── docs/ARCHITECTURE.md    # v2 design, data model, API, frontend and roadmap
├── streamlit_app/          # Streamlit UI dashboard
│   ├── app.py              # Main dashboard entrypoint
│   ├── pages/              # Dashboard pages (Player Stats, Clusters, Model Predictions)
│   └── utils/data.py       # Shared cached data loaders
├── PROJECT_DOCUMENTATION.md # Detailed technical breakdown & architectural guide
├── tests/                  # Pytest suite (helpers, data integrity, models, dashboard smoke tests)
├── pyproject.toml          # Project metadata and pytest configuration
├── requirements.txt        # Pinned runtime dependencies
├── requirements-dev.txt    # Adds test dependencies
└── README.md               # Project overview
```

---

## 🚀 Quick Start Guide

### 1. Clone the Repository
```bash
git clone https://github.com/tsetan13821/NBAAnalyticsProject.git
cd NBAAnalyticsProject
```

### 2. Set Up Virtual Environment & Dependencies
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Run Pipelines & ML Models
The processed datasets and model are committed, so this step is optional. Run from the repository root:
```bash
# Rebuild every dataset and model from the cached raw data
python -m src.pipeline

# Also re-download raw player stats and game results from the NBA API
python -m src.pipeline --fetch

# Or run a single step, e.g. evaluate the MVP model via LOOCV
python -m src.models.mvp_prediction
```

The last pipeline step, `python -m src.export_db`, builds the read-only serving database (`backend/data/nba.db`) used by the v2 API.

### 4. Launch Streamlit Web Application
```bash
streamlit run streamlit_app/app.py
```

### 5. Run the API (v2)
Build the serving database once, then start the API from the `backend/` folder:
```bash
python -m src.export_db
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://localhost:8000/docs for interactive API documentation.

### 6. Run the Web App (v2)
With the API running, start the Next.js app from the `frontend/` folder (Node.js 24):
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:3000. The app reads the API address from `API_URL` (default `http://localhost:8000`); copy `.env.example` to `.env.local` to change it.

### 7. Or Run Everything in Docker
No local Python or Node setup needed. The API image builds the database itself.
```bash
docker compose up --build
# Web app: http://localhost:3000    API docs: http://localhost:8000/docs

# If a port is already in use, choose other host ports
WEB_PORT=3001 API_PORT=8001 docker compose up --build
```

### 8. Run Tests
```bash
pip install -r requirements-dev.txt
pytest

# API tests and lint (needs the database from python -m src.export_db)
cd backend
pip install -r requirements-dev.txt
ruff check .
pytest

# Web app: types, lint, unit tests
cd ../frontend
npm run typecheck
npm run lint
npm test
```
Tests run on the committed datasets (no NBA API calls) and also run automatically on GitHub Actions for every push and pull request.

If you change the API on purpose, regenerate its committed schema with `python -m scripts.export_openapi` from `backend/`, then the frontend's types with `npm run gen:api` from `frontend/`.

---

## 📜 License

This project is open-sourced under the terms of the included [LICENSE](LICENSE) file.
