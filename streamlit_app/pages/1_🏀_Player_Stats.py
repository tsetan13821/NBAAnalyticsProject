import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Player Stats & Comparison", page_icon="🏀", layout="wide")

st.title("🏀 Player Comparison")
st.markdown("Compare players across different metrics using raw statistical percentile rankings.")

@st.cache_data
def load_data(category):
    # Mapping category to file
    file_map = {
        "All Players": "data/raw/nba_player_stats.csv",
        "Scorers": "data/processed/scorer_data.csv",
        "Playmakers": "data/processed/playmaker_data.csv",
        "Defenders": "data/processed/defensive_player_data.csv",
        "Rebounders": "data/processed/rebounder_data.csv"
    }
    
    file_path = file_map.get(category)
    if not os.path.exists(file_path):
        st.error(f"Data file not found: {file_path}")
        return pd.DataFrame()
    return pd.read_csv(file_path)

def compute_percentiles(df_season, metrics):
    percentiles = pd.DataFrame()
    percentiles['PLAYER_NAME'] = df_season['PLAYER_NAME']
    if 'TEAM_ABBREVIATION' in df_season.columns:
        percentiles['TEAM'] = df_season['TEAM_ABBREVIATION']
    
    for m in metrics:
        if m in df_season.columns:
            # lower is better for DEF_RATING and TOV
            if m in ['DEF_RATING', 'TOV']:
                percentiles[m] = df_season[m].rank(pct=True, ascending=False) * 100
            else:
                percentiles[m] = df_season[m].rank(pct=True) * 100
            percentiles[m] = percentiles[m].fillna(0)
    return percentiles

# Select category
category = st.selectbox("Select Player Category", ["All Players", "Scorers", "Playmakers", "Defenders", "Rebounders"])

with st.spinner("Loading Data..."):
    df = load_data(category)

if df.empty:
    st.stop()

# Season selection
seasons = sorted(df['SEASON'].unique(), reverse=True)
selected_season = st.selectbox("Select Season", seasons)

# Filter by season
df_season = df[df['SEASON'] == selected_season].copy()

# Define metrics dynamically based on category
if category == "Scorers":
    metrics = ["PTS", "TS_PCT", "USG_PCT", "FG3_PCT", "EFG_PCT", "OFF_RATING"]
elif category == "Playmakers":
    metrics = ["AST", "AST_TO", "AST_PCT", "USG_PCT", "PTS", "MIN"]
elif category == "Defenders":
    metrics = ["STL", "BLK", "DEF_RATING", "DREB_PCT", "MIN", "REB"]
elif category == "Rebounders":
    metrics = ["REB", "OREB_PCT", "DREB_PCT", "REB_PCT", "MIN", "PTS"]
else:
    metrics = ["PTS", "AST", "REB", "STL", "BLK", "TS_PCT", "USG_PCT", "PIE"]

players_list = sorted(df_season['PLAYER_NAME'].dropna().unique())

st.divider()

col1, col2 = st.columns(2)

with col1:
    player1 = st.selectbox("Player 1", options=players_list, index=0)
with col2:
    p2_index = min(1, len(players_list)-1) if len(players_list) > 1 else 0
    player2 = st.selectbox("Player 2", options=players_list, index=p2_index)

if player1 and player2:
    with st.spinner("Calculating percentiles & generating charts..."):
        percentiles_df = compute_percentiles(df_season, metrics)
        
        # Get data for player 1
        p1_mask = df_season['PLAYER_NAME'] == player1
        p1_raw = df_season[p1_mask].iloc[0]
        p1_pct = percentiles_df[percentiles_df['PLAYER_NAME'] == player1].iloc[0]
        
        # Get data for player 2
        p2_mask = df_season['PLAYER_NAME'] == player2
        p2_raw = df_season[p2_mask].iloc[0]
        p2_pct = percentiles_df[percentiles_df['PLAYER_NAME'] == player2].iloc[0]
        
        table_metrics = [m for m in metrics if m in p1_pct.index]
        
        # Build DataFrame for Display
        st.subheader("Comparison Percentiles vs Category Average")
        
        comparison_data = []
        p1_row = {"Player": f"{player1} ({p1_raw.get('TEAM_ABBREVIATION', 'N/A')})"}
        p2_row = {"Player": f"{player2} ({p2_raw.get('TEAM_ABBREVIATION', 'N/A')})"}
        
        for m in table_metrics:
            p1_row[m] = f"{p1_pct[m]:.1f}"
            p2_row[m] = f"{p2_pct[m]:.1f}"
            
        comparison_data.extend([p1_row, p2_row])
        st.dataframe(pd.DataFrame(comparison_data).set_index("Player"), use_container_width=True)
        
        st.subheader("Raw Stats")
        raw_data = []
        r1_row = {"Player": f"{player1} ({p1_raw.get('TEAM_ABBREVIATION', 'N/A')})"}
        r2_row = {"Player": f"{player2} ({p2_raw.get('TEAM_ABBREVIATION', 'N/A')})"}
        for m in table_metrics:
            # format differently based on metric
            if "PCT" in m or m in ["PIE"]:
                r1_row[m] = f"{p1_raw[m]:.3f}"
                r2_row[m] = f"{p2_raw[m]:.3f}"
            else:
                r1_row[m] = f"{p1_raw[m]:.1f}"
                r2_row[m] = f"{p2_raw[m]:.1f}"
        
        raw_data.extend([r1_row, r2_row])
        st.dataframe(pd.DataFrame(raw_data).set_index("Player"), use_container_width=True)
        
        # Radar Chart
        st.subheader("Radar Chart")
        
        fig = go.Figure()

        # Close the loop for radar chart
        theta = table_metrics + [table_metrics[0]]
        r_p1 = [p1_pct[m] for m in table_metrics] + [p1_pct[table_metrics[0]]]
        r_p2 = [p2_pct[m] for m in table_metrics] + [p2_pct[table_metrics[0]]]

        fig.add_trace(go.Scatterpolar(
            r=r_p1,
            theta=theta,
            fill='toself',
            name=player1,
            line_color='blue',
            opacity=0.7
        ))
        
        fig.add_trace(go.Scatterpolar(
            r=r_p2,
            theta=theta,
            fill='toself',
            name=player2,
            line_color='red',
            opacity=0.7
        ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            showlegend=True,
            title="Percentile Comparison (0-100)"
        )
        
        st.plotly_chart(fig, use_container_width=True)
