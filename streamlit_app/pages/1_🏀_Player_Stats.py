import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Player Stats & Comparison", page_icon="🏀", layout="wide")

st.title("🏀 Player Comparison")
st.markdown("Compare players across different metrics using raw statistical percentile rankings. Select a comparison mode to change the radar chart metrics.")

@st.cache_data
def load_data():
    file_path = "data/raw/nba_player_stats.csv"
    if not os.path.exists(file_path):
        st.error(f"Data file not found: {file_path}")
        return pd.DataFrame()
    df = pd.read_csv(file_path)
    
    # Infer lifetime position for filtering
    lifetime = df.groupby('PLAYER_NAME').sum(numeric_only=True).reset_index()
    def _infer(row):
        gp = max(1, row.get('GP', 1))
        ast = row.get('AST', 0) / gp
        reb = row.get('REB', 0) / gp
        blk = row.get('BLK', 0) / gp
        
        if reb >= 8.5 or (reb >= 7.5 and blk >= 1.2): return "Center (C)"
        if reb >= 6.5:
            if ast >= 5.0: return "Small Forward (SF)"
            return "Power Forward (PF)"
        if ast >= 5.5: return "Point Guard (PG)"
        if reb >= 5.5: return "Small Forward (SF)"
        if ast >= 3.5: return "Point Guard (PG)"
        return "Shooting Guard (SG)"
    
    lifetime['INFERRED_POS'] = lifetime.apply(_infer, axis=1)
    pos_map = dict(zip(lifetime['PLAYER_NAME'], lifetime['INFERRED_POS']))
    df['INFERRED_POS'] = df['PLAYER_NAME'].map(pos_map)
    
    return df

def compute_percentiles(df_season, metrics):
    percentiles = pd.DataFrame()
    percentiles['PLAYER_NAME'] = df_season['PLAYER_NAME']
    if 'TEAM_ABBREVIATION' in df_season.columns:
        percentiles['TEAM'] = df_season['TEAM_ABBREVIATION']
    
    for m in metrics:
        if m in df_season.columns:
            if m in ['DEF_RATING', 'TOV']:
                percentiles[m] = df_season[m].rank(pct=True, ascending=False) * 100
            else:
                percentiles[m] = df_season[m].rank(pct=True) * 100
            percentiles[m] = percentiles[m].fillna(0)
    return percentiles

# Select Comparison Templates rather than strict categories
comparison_mode = st.selectbox("Select Position Filter & Metrics", 
    ["Overall", "Point Guard (PG)", "Shooting Guard (SG)", "Small Forward (SF)", "Power Forward (PF)", "Center (C)"]
)

with st.spinner("Loading Data..."):
    df = load_data()

if df.empty:
    st.stop()

# Season selection
seasons = sorted(df['SEASON'].unique(), reverse=True)
selected_season = st.selectbox("Select Season", seasons)

# Filter by season
df_season = df[df['SEASON'] == selected_season].copy()

# Filter by inferred position if not 'Overall'
if comparison_mode != "Overall":
    df_filtered = df_season[df_season['INFERRED_POS'] == comparison_mode].copy()
else:
    df_filtered = df_season.copy()

# Define metrics dynamically based on Position Template
if comparison_mode == "Point Guard (PG)":
    metrics = ["AST", "AST_TO", "PTS", "STL", "FG3_PCT", "USG_PCT"]
elif comparison_mode == "Shooting Guard (SG)":
    metrics = ["PTS", "FG3_PCT", "TS_PCT", "AST", "STL", "USG_PCT"]
elif comparison_mode == "Small Forward (SF)":
    metrics = ["PTS", "REB", "AST", "STL", "TS_PCT", "DEF_RATING"]
elif comparison_mode == "Power Forward (PF)":
    metrics = ["REB", "PTS", "BLK", "OREB_PCT", "DEF_RATING", "EFG_PCT"]
elif comparison_mode == "Center (C)":
    metrics = ["REB", "BLK", "DREB_PCT", "OREB_PCT", "DEF_RATING", "EFG_PCT"]
else:
    metrics = ["PTS", "AST", "REB", "STL", "BLK", "TS_PCT", "USG_PCT", "PIE"]

players_list = sorted(df_filtered['PLAYER_NAME'].dropna().unique())

if not players_list:
    st.warning(f"No players found for {comparison_mode} in {selected_season}.")
    st.stop()

st.divider()

col1, col2 = st.columns(2)

with col1:
    player1 = st.selectbox("Player 1", options=players_list, index=0)
with col2:
    p2_index = min(1, len(players_list)-1) if len(players_list) > 1 else 0
    player2 = st.selectbox("Player 2", options=players_list, index=p2_index)

if player1 and player2:
    with st.spinner("Calculating percentiles & generating charts..."):
        # Calculate percentiles relative to the selected group (position or overall)
        percentiles_df = compute_percentiles(df_filtered, metrics)
        
        # Get data for player 1
        p1_mask = df_filtered['PLAYER_NAME'] == player1
        p1_raw = df_filtered[p1_mask].iloc[0]
        p1_pct = percentiles_df[percentiles_df['PLAYER_NAME'] == player1].iloc[0]
        
        # Get data for player 2
        p2_mask = df_filtered['PLAYER_NAME'] == player2
        p2_raw = df_filtered[p2_mask].iloc[0]
        p2_pct = percentiles_df[percentiles_df['PLAYER_NAME'] == player2].iloc[0]
        
        table_metrics = [m for m in metrics if m in p1_pct.index]
        
        # Build DataFrame for Display
        group_name = "League" if comparison_mode == "Overall" else comparison_mode
        st.subheader(f"Comparison Percentiles vs {group_name} Average")
        
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
        st.subheader(f"Radar Chart ({comparison_mode} Metrics)")
        
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
