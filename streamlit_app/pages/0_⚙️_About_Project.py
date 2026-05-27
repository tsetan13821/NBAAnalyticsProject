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
        Instead of relying on traditional positions (Guard, Forward, Center), we used **K-Means Clustering** (and PCA for dimensionality reduction) 
        to group players based on their actual on-court behavior (e.g., scoring volume, usage rate, rebounding percentages, assist-to-turnover ratios). 
        This results in modern archetypes like *Elite Scorers*, *Playmakers*, and *Defensive Anchors*.
        """)
        
    with st.expander("🔮 Next Matchup Predictor"):
        st.markdown("""
        To predict game outcomes, we trained tree-based classifiers purely on situational momentum. Features include trailing win-percentages 
        overall, at home, and on the road. The model learns how significantly home-court advantage and recent hot-streaks impact the final score.
        """)

with col2:
    with st.expander("⭐ All-Star & MVP Predictions"):
        st.markdown("""
        Using historical award voting and player statistics, we trained classification and regression algorithms to predict the 
        likelihood of a player receiving All-Star or MVP honors. The models identify which statistical thresholds historically trigger award recognition.
        """)

st.header("🛠️ Tech Stack & Data Pipeline")
st.markdown("""
* **Frontend:** Streamlit 
* **Data Manipulation:** Pandas, NumPy
* **Machine Learning:** Scikit-Learn, SciPy
* **Visualizations:** Plotly, Altair, Matplotlib, Seaborn
""")

st.info("The raw data for this project is systematically fetched and processed through custom ETL scripts located in the `src/data_pipeline` directory, ensuring models are trained on clean, normalized statistics.")

st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>Developed for combining the love of Basketball with Data Science and AI.</p>", unsafe_allow_html=True)
