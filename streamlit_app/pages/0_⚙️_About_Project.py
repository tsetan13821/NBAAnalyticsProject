import streamlit as st

st.set_page_config(page_title="About Project", page_icon="⚙️", layout="wide")

st.title("⚙️ About This Project")
st.markdown("---")

st.markdown("""
### 🏀 Project Overview
The **NBA AI & Analytics Dashboard** is an end-to-end data science project designed to extract actionable insights from raw NBA statistics. 
By leveraging modern data pipelines and machine learning algorithms, this platform moves beyond traditional box scores to provide 
predictive analytics, player archetyping, and matchup forecasting.
""")

st.header("🧠 Machine Learning Models")
st.markdown("We deployed several tailored machine learning models to power the insights across this dashboard:")

col1, col2 = st.columns(2)

with col1:
    with st.expander("📊 Player Clustering (Unsupervised ML)"):
        st.markdown("""
        Instead of relying on traditional positions, each player-season gets four standardized composite scores (Scorer, Playmaker,
        Rebounder, Defensive Player) built from per-game and rate stats such as points, usage, true shooting, assist and rebound
        percentages, steals, blocks and defensive rating. The highest score sets the archetype, and **1D K-Means clustering** then
        splits each archetype into *Elite*, *Very Good* and *Average* tiers.
        """)
        
    with st.expander("🔮 Next Matchup Predictor"):
        st.markdown("""
        An **XGBoost** classifier predicts whether the home team wins using each team's season-to-date win percentage overall,
        at home and on the road (computed only from games played before the matchup). It is trained on earlier seasons and
        tested on the most recent one; it performs about as well as simply picking the team with the better record.
        """)

with col2:
    with st.expander("⭐ All-Star & MVP Predictions"):
        st.markdown("""
        **MVP:** an **XGBoost** classifier trained on past MVP winners, using season-normalized (Z-score) stats, team success and a
        "won last year" voter-fatigue flag, with separate feature sets for the 2000-08 and 2008-present eras. Evaluated with
        leave-one-season-out cross-validation.

        **All-Star:** not a trained model: a hand-weighted Impact Score ranks eligible players and fills 6G / 6F / 3C slots per conference.
        """)

st.header("🛠️ Tech Stack & Data Pipeline")
st.markdown("""
* **Frontend:** Streamlit 
* **Data Manipulation:** Pandas, NumPy
* **Data Source:** `nba_api` (NBA.com stats endpoints)
* **Machine Learning:** XGBoost, Scikit-Learn
* **Visualizations:** Plotly, Altair, Matplotlib, Seaborn
""")

st.info("The raw data for this project is systematically fetched and processed through custom scripts in `src/` (run them all with `python -m src.pipeline`), ensuring models are trained on clean, normalized statistics.")

st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>Developed for combining the love of Basketball with Data Science and AI.</p>", unsafe_allow_html=True)
