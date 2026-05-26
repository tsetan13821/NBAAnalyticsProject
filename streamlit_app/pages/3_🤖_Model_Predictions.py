import streamlit as st
import pandas as pd
import altair as alt
import sys
import os

# Add root project directory to sys.path so we can import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.models.mvp_prediction import apply_mvp_candidate_filters, feature_engineering, test_season, run_loocv

st.set_page_config(page_title="MVP Predictions", page_icon="🤖", layout="wide")

st.title("🤖 MVP Prediction Model")
st.markdown("""
This tool uses a Machine Learning model (**XGBoost**) paired with a **Leave-One-Season-Out** cross-validation approach. 

### 🧠 Model Intelligence
In addition to basic box score stats, this model trains on advanced engineered features:
*   **Total Offensive Load**: Combines Usage Rate and Assist Percentage to capture how much of a team's offense runs directly through the player's hands.
*   **On/Off Proxy Math**: Takes a player's `Net Rating` and subtracts their team's average point differential to detect true "carry" value vs playing on a superteam.
*   **Voter Fatigue Penalty**: The algorithm identifies if a player won the previous year, learning historically how difficult it is for humans to award the same player three times in a row.
*   **Two-Way Impact**: Weighs "Stocks" (Steals + Blocks) alongside inverted defensive ratings to reward elite two-way stars.
*   **Availability Grading**: Rather than just passing a games-played cut-off, games played are Z-scored, severely punishing highly-injured stars compared to ironmen.
""")

@st.cache_data
def load_and_prep_data():
    """Loads CSV and applies initial filters"""
    df = pd.read_csv("data/processed/mvp_data.csv")
    # Clean whitespace strings from the names
    df['PLAYER_NAME'] = df['PLAYER_NAME'].astype(str).str.strip()
    df['SEASON'] = df['SEASON'].astype(str).str.strip()
    return df

def run_prediction_for_ui(target_season):
    df = load_and_prep_data()
    df = apply_mvp_candidate_filters(df)
    df, z_features = feature_engineering(df)
    df[z_features] = df[z_features].fillna(0)
    
    result = test_season(df, z_features, target_season)
    return result

df = load_and_prep_data()
available_seasons = sorted(df['SEASON'].unique(), reverse=True)

# Tabs
tab1, tab2 = st.tabs(["🎯 Single Season Prediction", "📈 All-Time Historical Accuracy"])

with tab1:
    st.markdown("Predict the MVP of a selected season without any **future bias**.")
    # Layout: select box
    col_season, _ = st.columns([1, 2])
    with col_season:
        selected_season = st.selectbox("Select Season to Predict", available_seasons)
        run_btn = st.button("Run Prediction", type="primary")

    st.divider()

    if run_btn:
        with st.spinner(f"Training XGBoost model on all other seasons to predict {selected_season}..."):
            res = run_prediction_for_ui(selected_season)
            
            if res:
                # Display Topline Result
                st.subheader(f"Results for the {selected_season} Season")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.success(f"**👑 Model Predicted MVP:** {res['PREDICTED_MVP']}")
                with col2:
                    st.info(f"**🏆 Actual Real-Life MVP:** {res['ACTUAL_MVP']}")
                
                if res['CORRECT']:
                    st.balloons()
                
                st.markdown("### Top 10 Candidates (Model Probability)")
                
                # Format Data for Chart
                chart_df = pd.DataFrame(res['TOP_10_CANDIDATES'])
                # Round probability score for display
                chart_df['Probability %'] = (chart_df['MVP_PROB_SCORE'] * 100).round(2)
                
                # Altair Bar Chart
                chart = alt.Chart(chart_df).mark_bar(cornerRadiusEnd=4, height=20).encode(
                    x=alt.X('MVP_PROB_SCORE:Q', title='Model Probability Score', scale=alt.Scale(domain=[0, 1])),
                    y=alt.Y('PLAYER_NAME:N', sort='-x', title='Player'),
                    color=alt.Color('MVP_PROB_SCORE:Q', scale=alt.Scale(scheme='blues'), legend=None),
                    tooltip=['PLAYER_NAME', 'Probability %']
                ).properties(height=400)
                
                # Show chart and raw data side-by-side
                c_chart, c_data = st.columns([2, 1])
                with c_chart:
                    st.altair_chart(chart, use_container_width=True)
                with c_data:
                    st.dataframe(
                        chart_df[['PLAYER_NAME', 'Probability %']].rename(columns={'PLAYER_NAME': 'Player'}),
                        hide_index=True,
                        use_container_width=True
                    )
                    
            else:
                st.error("No valid filtered candidates found for this season (or missing data).")

with tab2:
    st.markdown("### Model Evaluation Over All Available Seasons")
    st.markdown("This validates the model on every single year via Leave-One-Season-Out cross-validation.")
    if st.button("Run Historical Accuracy Check (Takes ~5 seconds)", type="primary"):
        with st.spinner("Training model sequentially across all 26 seasons..."):
            loocv_results = run_loocv()
            st.success(f"**Overall MVP Prediction Accuracy:** {loocv_results['accuracy_str']}")
            
            # Formating a nice DataFrame to display
            history_data = []
            for item in loocv_results['results']:
                history_data.append({
                    "Season": item['SEASON'],
                    "Predicted MVP": item['PREDICTED_MVP'],
                    "Actual MVP": item['ACTUAL_MVP'],
                    "Correct?": "✅ Yes" if item['CORRECT'] else "❌ No"
                })
            
            history_df = pd.DataFrame(history_data)
            
            st.dataframe(history_df, use_container_width=True, hide_index=True)