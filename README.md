# ?? NBA Analytics Project

![Python](https://img.shields.io/badge/Python-3.x-blue?style=flat&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red?style=flat&logo=streamlit)
![Machine Learning](https://img.shields.io/badge/Machine%20Learning-Scikit--learn-orange)

An end-to-end data science and machine learning project focused on NBA player statistics, awards predictions, and player profiling. 

## ?? Features

- **Automated Data Pipeline**: Fetches, cleans, and processes raw NBA player stats to dynamically build datasets (e.g., MVP data).
- **Machine Learning Models**:
  - **MVP Prediction**: Rolling and static MVP prediction models achieving **73.1% historical accuracy** over the last 26 seasons.
  - **All-Star Prediction**: Predicts likelihood of players being selected as All-Stars.
  - **Next Game Prediction**: Forecasts player performance for upcoming games.
  - **Player Clustering**: Unsupervised learning models to group players by playstyles.
- **Interactive Dashboard**: A multi-page Streamlit application with the following tools:
  - ?? Player Stats Analysis
  - ?? Team Insights
  - ?? Model Predictions
  - ?? Player Clusters
- **Exploratory Data Analysis (EDA)**: Jupyter notebooks containing comprehensive EDA and model testing.

## ?? Project Structure

`	ext
NBAAnalyticsProject/
+-- config/                 # Configuration files (config.yaml)
+-- data/
�   +-- processed/          # Cleaned, ready-to-use data (mvp_data.csv)
�   +-- raw/                # Raw ingested data (nba_player_stats.csv)
+-- notebooks/              # Jupyter Notebooks for EDA and Model Testing
+-- saved_models/           # Serialized/Exported ML models
+-- src/                    # Source code for data pipelines and models
�   +-- data_pipeline/      # Scripts to fetch, clean, and build datasets
�   +-- models/             # ML model implementations and training scripts
+-- streamlit_app/          # Streamlit UI
�   +-- pages/              # Specific dashboard pages
�   +-- utils/              # UI helper functions and visualization scripts
+-- tests/                  # Unit tests for pipelines and models
+-- pyproject.toml          # Project metadata and dependencies
+-- requirements.txt        # Python dependencies
+-- README.md               # Project documentation
`

## ?? Getting Started

### 1. Clone the repository
`ash
git clone https://github.com/tsetan13821/NBAAnalyticsProject.git
cd NBAAnalyticsProject
`

### 2. Set up the environment
Create a virtual environment and install dependencies:
`ash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
`

### 3. Run the Data Pipeline (Optional)
If you wish to re-fetch and process the data:
`ash
python src/data_pipeline/raw_data_fetch.py
python src/data_pipeline/clean_data.py
python src/data_pipeline/build_mvp_dataset.py
`

### 4. Launch the Streamlit App
`ash
cd streamlit_app
streamlit run app.py
`

## ?? Testing

To run the unit tests for the data pipeline and machine learning models:
`ash
pytest tests/
`

## ?? License

This project is open-sourced under the terms of the included LICENSE file.
