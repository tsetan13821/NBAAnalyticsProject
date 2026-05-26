import streamlit as st
import pandas as pd
import numpy as np
import os
import joblib
import altair as alt

st.set_page_config(page_title="Next Game Prediction", page_icon="??", layout="wide")

st.title("?? Next Matchup Predictor")
st.markdown("""
Predict the outcome of an upcoming NBA game based on team momentum and venue strength! 
This model relies purely on situational form (Overall Win %, Home Win %, and Road Win %) rather than historical head-to-head records.
""")

@st.cache_resource
def load_model():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    model_path = os.path.join(base_dir, "saved_models", "next_game_model.pkl")
    if os.path.exists(model_path):
        return joblib.load(model_path)
    return None

@st.cache_data
def load_game_data():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_path = os.path.join(base_dir, "data", "processed", "game_matchups.csv")
    if not os.path.exists(data_path):
        return None
    df = pd.read_csv(data_path)
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    return df

df = load_game_data()
model = load_model()

if model is None or df is None:
    st.warning("Model or Matchup data not found. Please run python src/models/next_game_prediction.py first.")
    st.stop()

# Get all unique teams
teams = sorted(list(set(df['HOME_TEAM_ABBREVIATION'].unique().tolist() + df['AWAY_TEAM_ABBREVIATION'].unique().tolist())))

# We extract the latest stats
latest_stats = {}
for t in teams:
    home_games = df[df['HOME_TEAM_ABBREVIATION'] == t]
    away_games = df[df['AWAY_TEAM_ABBREVIATION'] == t]
    
    overall_pct = 0.5; home_pct = 0.5; away_pct = 0.5
    if not home_games.empty:
        home_pct = home_games.iloc[-1]['HOME_Home_WinPCT']
        overall_pct = home_games.iloc[-1]['HOME_Overall_WinPCT']
    if not away_games.empty:
        away_pct = away_games.iloc[-1]['AWAY_Away_WinPCT']
        if not home_games.empty and away_games.index[-1] > home_games.index[-1]:
            overall_pct = away_games.iloc[-1]['AWAY_Overall_WinPCT']
        elif home_games.empty:
            overall_pct = away_games.iloc[-1]['AWAY_Overall_WinPCT']
            
    latest_stats[t] = {
        'Overall_WinPCT': overall_pct,
        'Home_WinPCT': home_pct,
        'Away_WinPCT': away_pct
    }

st.sidebar.header("Matchup Selection ??")
home_team = st.sidebar.selectbox("Select Home Team ??", teams, index=teams.index('BOS') if 'BOS' in teams else 0)
default_away = 'DAL' if 'DAL' in teams else teams[1]
away_team = st.sidebar.selectbox("Select Away Team ??", teams, index=teams.index(default_away) if default_away in teams else 1)

if home_team == away_team:
    st.error("Please select two different teams.")
    st.stop()

st.sidebar.markdown("---")
st.sidebar.markdown("### Override Momentum (Optional)")
st.sidebar.caption("Tweak these sliders to simulate injuries or sudden hot-streaks. These feed directly into the XGBoost predictors.")
home_overall = st.sidebar.slider(f"{home_team} Overall Win %", 0.0, 1.0, float(latest_stats[home_team]['Overall_WinPCT']), 0.01)
home_home = st.sidebar.slider(f"{home_team} Home Win %", 0.0, 1.0, float(latest_stats[home_team]['Home_WinPCT']), 0.01)

st.sidebar.markdown("---")
away_overall = st.sidebar.slider(f"{away_team} Overall Win %", 0.0, 1.0, float(latest_stats[away_team]['Overall_WinPCT']), 0.01)
away_away = st.sidebar.slider(f"{away_team} Road Win %", 0.0, 1.0, float(latest_stats[away_team]['Away_WinPCT']), 0.01)

# Team Banners
col_h, col_vs, col_a = st.columns([3, 1, 3])

with col_h:
    st.markdown(f"<div style='border: 2px solid #1E90FF; padding: 20px; border-radius: 10px; background-color: rgba(30, 144, 255, 0.1);'><h1 style='text-align: center; color: #1E90FF; margin: 0;'>?? {home_team}</h1><br><p style='text-align: center; margin: 0; font-size: 1.2rem;'>Overall Form: <b>{home_overall*100:.1f}%</b><br>Home Stadium Form: <b>{home_home*100:.1f}%</b></p></div>", unsafe_allow_html=True)
    
with col_vs:
    st.markdown("<br><h1 style='text-align: center; color: #888; font-size: 3rem;'>VS</h1>", unsafe_allow_html=True)

with col_a:
    st.markdown(f"<div style='border: 2px solid #FF4500; padding: 20px; border-radius: 10px; background-color: rgba(255, 69, 0, 0.1);'><h1 style='text-align: center; color: #FF4500; margin: 0;'>?? {away_team}</h1><br><p style='text-align: center; margin: 0; font-size: 1.2rem;'>Overall Form: <b>{away_overall*100:.1f}%</b><br>Away Form: <b>{away_away*100:.1f}%</b></p></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Prepare features
features = pd.DataFrame([{
    'HOME_Overall_WinPCT': home_overall,
    'HOME_Home_WinPCT': home_home,
    'AWAY_Overall_WinPCT': away_overall,
    'AWAY_Away_WinPCT': away_away,
    'WinPCT_Diff': home_overall - away_overall,
    'HomeAway_Diff': home_home - away_away
}])

# PREDICTION
col_pred_btn, col_blank, col_blank2 = st.columns([1, 1, 1])
with col_pred_btn:
    predict_clicked = st.button("? INITIALIZE PREDICTION", use_container_width=True, type="primary")

if predict_clicked:
    st.markdown("### ?? Prediction Result")
    probabilities = model.predict_proba(features)[0]
    home_prob = probabilities[1]
    away_prob = probabilities[0]
    
    if home_prob > away_prob:
        st.success(f"**{home_team}** defends home court with a **{home_prob*100:.1f}%** chance of winning!")
    else:
        st.info(f"**{away_team}** steals the road victory with a **{away_prob*100:.1f}%** chance of winning!")

    # Altair Horizontal Bar chart for probability
    prob_df = pd.DataFrame({
        'Team': [home_team, away_team],
        'Probability': [home_prob, away_prob],
        'Type': ['Home', 'Away']
    })
    
    chart = alt.Chart(prob_df).mark_bar(cornerRadiusEnd=4, height=40).encode(
        x=alt.X('Probability:Q', scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format='%', title='Model Confidence')),
        y=alt.Y('Team:N', sort='-x', title=None, axis=alt.Axis(labelFontSize=14, labelFontWeight='bold')),
        color=alt.Color('Type:N', scale=alt.Scale(domain=['Home', 'Away'], range=['#1E90FF', '#FF4500']), legend=None),
        tooltip=['Team', alt.Tooltip('Probability:Q', format='.1%')]
    ).properties(height=200)
    
    st.altair_chart(chart, use_container_width=True)

st.divider()

# Historical momentum line chart
st.markdown(f"### ?? Momentum Tracking Over Recent Seasons")
st.markdown("How has each team's overall win percentage trended? (*Shows running win percentage over all historical games in dataset*)")

# Gather momentum for both teams
h_mom = df[(df['HOME_TEAM_ABBREVIATION'] == home_team) | (df['AWAY_TEAM_ABBREVIATION'] == home_team)].copy()
a_mom = df[(df['HOME_TEAM_ABBREVIATION'] == away_team) | (df['AWAY_TEAM_ABBREVIATION'] == away_team)].copy()

# Extract just the dates and overall win % for each team
def extract_momentum(team_data, team_abbr):
    records = []
    for _, row in team_data.iterrows():
        if row['HOME_TEAM_ABBREVIATION'] == team_abbr:
            records.append({'Date': row['GAME_DATE'], 'Win%': row['HOME_Overall_WinPCT'], 'Team': team_abbr})
        else:
            records.append({'Date': row['GAME_DATE'], 'Win%': row['AWAY_Overall_WinPCT'], 'Team': team_abbr})
    return pd.DataFrame(records)

h_df = extract_momentum(h_mom, home_team)
a_df = extract_momentum(a_mom, away_team)

combined_mom = pd.concat([h_df, a_df]).sort_values(by='Date')

# Altair line chart
line_chart = alt.Chart(combined_mom).mark_line(interpolate='monotone', strokeWidth=3).encode(
    x=alt.X('Date:T', title='Game Date', axis=alt.Axis(grid=False)),
    y=alt.Y('Win%:Q', scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format='%', title='Running Win %')),
    color=alt.Color('Team:N', scale=alt.Scale(domain=[home_team, away_team], range=['#1E90FF', '#FF4500']), legend=alt.Legend(title="Team", orient="top-left")),
    tooltip=['Team', 'Date:T', alt.Tooltip('Win%:Q', format='.1%')]
).properties(height=400)

st.altair_chart(line_chart, use_container_width=True)
