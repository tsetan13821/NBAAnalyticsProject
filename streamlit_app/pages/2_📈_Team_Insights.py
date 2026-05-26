import streamlit as st
import pandas as pd
import altair as alt
import os

st.set_page_config(page_title="Team Insights", page_icon="📈", layout="wide")

st.title("📈 Team Historical Insights")
st.markdown("Analyze team performance, win percentages, and championship history across the modern era.")

@st.cache_data
def load_team_data():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_path = os.path.join(base_dir, "data", "processed", "mvp_data.csv")
    
    if not os.path.exists(data_path):
        return None
        
    df = pd.read_csv(data_path)
    
    # Extract unique team seasons
    team_df = df[['SEASON', 'TEAM_ABBREVIATION', 'WINS', 'LOSSES', 'WinPCT']].drop_duplicates()
    
    # Map Champions
    champions = {
        '2000-01': 'LAL', '2001-02': 'LAL', '2002-03': 'SAS', '2003-04': 'DET',
        '2004-05': 'SAS', '2005-06': 'MIA', '2006-07': 'SAS', '2007-08': 'BOS',
        '2008-09': 'LAL', '2009-10': 'LAL', '2010-11': 'DAL', '2011-12': 'MIA',
        '2012-13': 'MIA', '2013-14': 'SAS', '2014-15': 'GSW', '2015-16': 'CLE',
        '2016-17': 'GSW', '2017-18': 'GSW', '2018-19': 'TOR', '2019-20': 'LAL',
        '2020-21': 'MIL', '2021-22': 'GSW', '2022-23': 'DEN', '2023-24': 'BOS'
    }
    
    def is_champ(row):
        return row['TEAM_ABBREVIATION'] == champions.get(row['SEASON'])
        
    team_df['IS_CHAMPION'] = team_df.apply(is_champ, axis=1)
    
    # Calculate starting year for line sorting
    team_df['Year_Start'] = team_df['SEASON'].apply(lambda x: int(str(x).split('-')[0]) if pd.notnull(x) and '-' in str(x) else 0)
    team_df = team_df.sort_values(by='Year_Start')
    
    return team_df

team_df = load_team_data()

if team_df is None:
    st.warning("Data not found. Please ensure the pipeline has fully processed mvp_data.csv.")
    st.stop()

# Get available teams
teams = sorted(team_df['TEAM_ABBREVIATION'].dropna().unique().tolist())

# UI Layout
col1, col2 = st.columns([1, 2.5])

with col1:
    st.subheader("🔍 Filter Franchise")
    selected_team = st.selectbox("Select a Team to Analyze:", teams, index=teams.index('LAL') if 'LAL' in teams else 0)
    
    st.markdown("---")
    
    team_specific = team_df[team_df['TEAM_ABBREVIATION'] == selected_team].copy()
    
    total_seasons = len(team_specific)
    total_wins = team_specific['WINS'].sum()
    total_losses = team_specific['LOSSES'].sum()
    overall_win_pct = total_wins / (total_wins + total_losses) if (total_wins + total_losses) > 0 else 0
    champs_won = team_specific['IS_CHAMPION'].sum()
    
    st.markdown(f"### {selected_team} Summary (Since 2000)")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("🏆 Championships", champs_won)
    with col_b:
        st.metric("📊 Overall Win %", f"{overall_win_pct*100:.1f}%")
        
    st.metric("📝 Total Record", f"{int(total_wins)} - {int(total_losses)}")
    
    # Need to handle edge cases if stats missing
    if not team_specific.empty:
        best_season = team_specific.loc[team_specific['WinPCT'].idxmax()]
        worst_season = team_specific.loc[team_specific['WinPCT'].idxmin()]
        
        st.markdown("**Best Single Season:**")
        st.success(f"**{best_season['SEASON']}** | {int(best_season['WINS'])}-{int(best_season['LOSSES'])}  ({best_season['WinPCT']*100:.1f}%)")
        
        st.markdown("**Worst Single Season:**")
        st.error(f"**{worst_season['SEASON']}** | {int(worst_season['WINS'])}-{int(worst_season['LOSSES'])}  ({worst_season['WinPCT']*100:.1f}%)")

with col2:
    st.subheader(f"📈 {selected_team} Win Percentage Over Time")
    
    # Create the chart
    base = alt.Chart(team_specific).encode(
        x=alt.X('SEASON:O', title='Season', sort=alt.SortField(field='Year_Start')),
        y=alt.Y('WinPCT:Q', title='Win Percentage', scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format='%'))
    )
    
    # Line
    line = base.mark_line(color='#1E90FF', strokeWidth=4)
    
    # Points
    points = base.mark_circle(size=80).encode(
        color=alt.condition(
            alt.datum.IS_CHAMPION,
            alt.value('#FFD700'), # Gold for champions
            alt.value('#1E90FF') # Blue for normal
        ),
        size=alt.condition(
            alt.datum.IS_CHAMPION,
            alt.value(300),
            alt.value(80)
        ),
        tooltip=['SEASON', 'WINS', 'LOSSES', alt.Tooltip('WinPCT:Q', format='.1%'), 'IS_CHAMPION']
    )
    
    chart = (line + points).properties(height=450).interactive()
    
    st.altair_chart(chart, use_container_width=True)
    
    st.caption("🟡 Large Gold circles highlight Championship-winning seasons!")

st.divider()

st.subheader("🔥 Top 10 Best Regular Season Teams (Modern Era)")
st.markdown("The 10 most successful individual team campaigns since 2000 based on regular season Win Percentage. *Do they hold the trophy to prove it?*")

top_10_teams = team_df.sort_values(by='WinPCT', ascending=False).head(10).copy()
top_10_teams['Rank'] = range(1, 11)
top_10_teams['Record'] = top_10_teams['WINS'].astype(int).astype(str) + " - " + top_10_teams['LOSSES'].astype(int).astype(str)
top_10_teams['WinPCT_Display'] = (top_10_teams['WinPCT'] * 100).round(1).astype(str) + "%"
top_10_teams['Champion?'] = top_10_teams['IS_CHAMPION'].apply(lambda x: "🏆 Yes" if x else "❌ No")

display_cols = ['Rank', 'SEASON', 'TEAM_ABBREVIATION', 'Record', 'WinPCT_Display', 'Champion?']
top_10_teams_display = top_10_teams[display_cols].rename(columns={'SEASON': 'Season', 'TEAM_ABBREVIATION': 'Team', 'WinPCT_Display': 'Win %'})

# Display dataframe beautifully
st.dataframe(
    top_10_teams_display,
    column_config={
        "Rank": st.column_config.NumberColumn("Rank", format="%d"),
        "Season": "Season",
        "Team": "Team",
        "Record": "Record",
        "Win %": "Win %",
        "Champion?": "Won Finals?"
    },
    hide_index=True,
    use_container_width=True,
    height=400
)
