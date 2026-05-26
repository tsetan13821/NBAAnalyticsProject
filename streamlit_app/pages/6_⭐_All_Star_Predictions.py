import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="All-Star Predictions", page_icon="?", layout="wide")

st.title("? All-Star Predictions & Rosters")
st.markdown("""
This tool uses our **Impact Score Model** to retroactively build optimal All-Star rosters for each season.
The model strictly adheres to modern roster rules per conference:
*   **6 Guards**
*   **6 Forwards**
*   **3 Centers**

It penalizes "empty stats" by enforcing that no players are selected from a bottom-tier team (Seeds 11-15) and mathematically weighing Win percentage alongside their advanced individual efficiency.
""")

@st.cache_data
def load_data():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    file_path = os.path.join(base_dir, "data", "processed", "all_stars_master.csv")
    if not os.path.exists(file_path):
        return None
    df = pd.read_csv(file_path)
    return df

df = load_data()

if df is None:
    st.warning("All-Star data not found. Please run the All-Star prediction pipeline first.")
    st.stop()

seasons = sorted(df['SEASON'].unique(), reverse=True)
selected_season = st.selectbox("Select Season", seasons)

season_df = df[df['SEASON'] == selected_season]

# Create two columns, one for East, one for West
col_east, col_west = st.columns(2)

def render_conference_roster(conf_df, conf_name):
    st.markdown(f"### {conf_name}ern Conference")
    
    # Calculate some quick stats for the team
    avg_impact = conf_df['IMPACT_SCORE'].mean()
    avg_win = conf_df['WinPCT'].mean() * 100
    st.caption(f"Team Avg Impact: **{avg_impact:.1f}** | Avg Win%: **{avg_win:.1f}%**")
    
    # Display in a nice dataframe
    display_cols = ['PLAYER_NAME', 'TEAM_ABBREVIATION', 'POS', 'PTS', 'REB', 'AST', 'Conf_Seed', 'IMPACT_SCORE']
    styled_df = conf_df[display_cols].sort_values(by='IMPACT_SCORE', ascending=False)
    
    # Format the stats
    styled_df['IMPACT_SCORE'] = styled_df['IMPACT_SCORE'].round(1)
    
    # Rename columns for presentation
    styled_df = styled_df.rename(columns={
        'PLAYER_NAME': 'Player',
        'TEAM_ABBREVIATION': 'Team',
        'POS': 'Position',
        'Conf_Seed': 'Team Seed',
        'IMPACT_SCORE': 'Impact Score'
    })
    
    # Force index to 1-15
    styled_df.index = range(1, len(styled_df) + 1)
    
    st.dataframe(styled_df, use_container_width=True, height=560)

with col_east:
    east_data = season_df[season_df['Conference'] == 'East']
    render_conference_roster(east_data, 'East')

with col_west:
    west_data = season_df[season_df['Conference'] == 'West']
    render_conference_roster(west_data, 'West')

st.divider()
st.markdown("### ?? All-Time Most Selections (Based on Model)")
col_all_time = st.columns(1)[0]
with col_all_time:
    selections = df['PLAYER_NAME'].value_counts().head(20).reset_index()
    selections.columns = ['Player', 'Model All-Star Selections']
    selections.index = range(1, len(selections) + 1)
    st.dataframe(selections, use_container_width=True)

