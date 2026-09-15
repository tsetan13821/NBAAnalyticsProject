# 🏀 NBA Analytics & Machine Learning Dashboard

![Python](https://img.shields.io/badge/Python-3.x-blue?style=flat&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red?style=flat&logo=streamlit)
![XGBoost](https://img.shields.io/badge/Machine%20Learning-XGBoost-orange)
![Scikit-Learn](https://img.shields.io/badge/Clustering-K--Means-green)

An end-to-end data science and machine learning platform focused on NBA player statistics, predictive awards forecasting, player playstyle clustering, and game outcome modeling.

> 📖 **Complete Documentation**: For an in-depth walkthrough of the data collection API endpoints, feature engineering math, era normalization rules, and machine learning architectures, see [PROJECT_DOCUMENTATION.md](file:///c:/Users/ten2i/OneDrive/Desktop/NBAAnalytics/NBAAnalyticsProject/PROJECT_DOCUMENTATION.md).

---

## ✨ Features

- **Automated Data Pipeline**: Ingests, cleans, and processes raw multi-season NBA statistics via official API wrappers (`Base` and `Advanced` endpoints).
- **Machine Learning Models**:
  - **MVP Prediction**: XGBoost model using Leave-One-Season-Out Cross Validation (LOOCV), achieving **73.1% historical accuracy** over the past 26 seasons.
  - **All-Star Prediction**: Position-constrained impact scoring model predicting Eastern and Western conference selections.
  - **Player Archetype Clustering**: Unsupervised composite scoring and 1D K-Means clustering to classify players by playstyle (`Scorer`, `Playmaker`, `Rebounder`, `Defensive Player`) and performance tiers (`Elite`, `Very Good`, `Average`).
  - **Next Game Prediction**: XGBoost game outcome forecast based on team momentum and home/away differentials.
- **Interactive Streamlit Dashboard**: Full visual analytics web application featuring player lookups, team efficiency quadrant charts, live MVP model prediction runners, and clustering visualizations.

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
│   ├── data_collection.py  # Script to ingest multi-season stats from NBA API
│   ├── data_pipeline/      # Data pipeline scripts (standings fetch, MVP dataset build)
│   └── models/             # Machine learning implementations (MVP, All-Star, Clustering, Next Game)
├── streamlit_app/          # Streamlit UI dashboard
│   ├── app.py              # Main dashboard entrypoint
│   └── pages/              # Dashboard pages (Player Stats, Clusters, Model Predictions)
├── PROJECT_DOCUMENTATION.md # Detailed technical breakdown & architectural guide
├── pyproject.toml          # Project metadata and dependencies
├── requirements.txt        # Python dependencies
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
```bash
# Data Collection from NBA API
python src/data_collection.py

# Build MVP Dataset with Team Standings
python src/data_pipeline/build_mvp_dataset.py

# Evaluate MVP XGBoost Model via LOOCV
python src/models/mvp_prediction.py

# Run Player Archetype Clustering Pipeline
python src/models/player_clustering.py
```

### 4. Launch Streamlit Web Application
```bash
cd streamlit_app
streamlit run app.py
```

---

## 📜 License

This project is open-sourced under the terms of the included [LICENSE](file:///c:/Users/ten2i/OneDrive/Desktop/NBAAnalytics/NBAAnalyticsProject/LICENSE) file.
