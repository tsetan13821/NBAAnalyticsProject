import streamlit as st
import pandas as pd
import altair as alt
import os

st.set_page_config(page_title="Player Clusters", page_icon="??", layout="wide")

st.title("?? NBA Player Clusters & Archetypes")
st.markdown("""
Explore player archetypes using **K-Means Clustering**. Players are grouped by their dominant stat profile (**Scorer, Playmaker, Rebounder, Defensive**) 
and then segmented into internal distinct tiers (**Elite, Very Good, Average**).
""")

@st.cache_data
def load_data():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    file_path = os.path.join(base_dir, "data", "processed", "clustered_players_master.csv")
    if not os.path.exists(file_path):
        return None
    df = pd.read_csv(file_path)
    return df

df = load_data()

if df is None:
    st.warning("Cluster data not found. Please run the player clustering pipeline first.")
    st.stop()

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filter Options")
seasons = sorted(df['SEASON'].unique(), reverse=True)
# Default to the most recent season (index 1) instead of "All Time" to prevent massive UI rendering delays
selected_season = st.sidebar.selectbox("Select Season", ["All Time"] + list(seasons), index=1)

clusters = df['Cluster'].unique()
selected_cluster = st.sidebar.multiselect("Select Archetypes", clusters, default=clusters)

tiers = ['Elite', 'Very Good', 'Average']
selected_tier = st.sidebar.multiselect("Select Tiers", tiers, default=tiers)

# Apply filters
filtered_df = df.copy()
if selected_season != "All Time":
    filtered_df = filtered_df[filtered_df['SEASON'] == selected_season]
if selected_cluster:
    filtered_df = filtered_df[filtered_df['Cluster'].isin(selected_cluster)]
if selected_tier:
    filtered_df = filtered_df[filtered_df['Tier'].isin(selected_tier)]

# --- TOP METRICS ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Players Filtered", len(filtered_df))
col2.metric("Elites Found", len(filtered_df[filtered_df['Tier'] == 'Elite']))
col3.metric("Avg Points (Filtered)", round(filtered_df['PTS'].mean(), 1))
col4.metric("Avg Minutes (Filtered)", round(filtered_df['MIN'].mean(), 1))

st.divider()

# --- INTERACTIVE SCATTER PLOT ---
st.markdown("### ?? Interactive Stat Explorer")
st.markdown("Compare players across different metrics. The chart is colored by their Tier.")

stat_cols = ['PTS', 'AST', 'REB', 'STL', 'BLK', 'USG_PCT', 'TS_PCT', 'MIN', 'PIE', 'NET_RATING']
scol1, scol2 = st.columns(2)
x_axis = scol1.selectbox("X-Axis Metric", stat_cols, index=stat_cols.index('USG_PCT'))
y_axis = scol2.selectbox("Y-Axis Metric", stat_cols, index=stat_cols.index('PTS'))

if len(filtered_df) > 0:
    if len(filtered_df) > 2000:
        st.warning("⚠️ **Too many players selected!** The interactive scatter plot is temporarily disabled because rendering thousands of data points will severely slow down your browser. Please select a specific season or narrower filters.")
    else:
        # Altair Scatter Plot
        scatter = alt.Chart(filtered_df).mark_circle(size=60).encode(
            x=alt.X(x_axis, scale=alt.Scale(zero=False)),
            y=alt.Y(y_axis, scale=alt.Scale(zero=False)),
            color=alt.Color('Tier', scale=alt.Scale(domain=['Elite', 'Very Good', 'Average'], range=['#FFD700', '#C0C0C0', '#CD7F32'])),
            tooltip=['PLAYER_NAME', 'SEASON', 'TEAM_ABBREVIATION', 'Cluster', 'Tier', x_axis, y_axis],
            shape='Cluster'
        ).interactive().properties(
            height=500
        )
        st.altair_chart(scatter)
else:
    st.info("No players match the current filter criteria.")

# --- TIER BREAKDOWNS ---
st.markdown("### 🏆 All-Time Top 20 Players by Category")
st.markdown("Showing the **absolute best 20 individual seasons** for each archetype across the entire historical dataset.")
clusters_list = list(clusters)
tabs = st.tabs(clusters_list)

def render_tier_table(cluster_name):
    # Bypass the sidebar filters using the raw `df` to get true all-time greats
    cluster_data = df[df['Cluster'] == cluster_name]
    if len(cluster_data) == 0:
        st.write("No players found for this category.")
        return
        
    # Sort by the archetype's specific machine learning dimension score
    score_col = f"{cluster_name}_Score"
    if score_col in cluster_data.columns:
        top_20 = cluster_data.sort_values(by=score_col, ascending=False).head(20)
    else:
        # Fallback sorting just in case
        fallback_sort = {'Scorer': 'PTS', 'Playmaker': 'AST', 'Rebounder': 'REB', 'Defensive Player': 'STL'}
        top_20 = cluster_data.sort_values(by=fallback_sort.get(cluster_name, 'PTS'), ascending=False).head(20)
        
    st.dataframe(
        top_20[['PLAYER_NAME', 'SEASON', 'TEAM_ABBREVIATION', 'Tier', 'PTS', 'AST', 'REB', 'STL', 'BLK', 'USG_PCT']]
        .set_index('PLAYER_NAME'),
        height=750
    )

for i, cluster in enumerate(clusters_list):
    with tabs[i]:
        render_tier_table(cluster)

# --- SIMILAR PLAYER FINDER ---
st.divider()
st.markdown("### ?? Find Similar Players")
st.markdown("Select a player to find who plays most similarly to them based on advanced clustered metrics.")

all_players = sorted(df['PLAYER_NAME'].dropna().unique())
target_player = st.selectbox("Search Player", all_players, index=all_players.index("Stephen Curry") if "Stephen Curry" in all_players else 0)

if target_player:
    player_history = df[df['PLAYER_NAME'] == target_player]
    if len(player_history) > 0:
        target_season_sel = st.selectbox("Select specific season for this player", sorted(player_history['SEASON'].unique(), reverse=True))
        
        target_vector = player_history[player_history['SEASON'] == target_season_sel]
        if len(target_vector) > 0:
            target_data = target_vector.iloc[0]
            st.write(f"**{target_data['PLAYER_NAME']} ({target_data['SEASON']})** - {target_data['Cluster']} | {target_data['Tier']}")
            
            # Simple euclidean distance finding based on the scores
            score_cols = ['Scorer_Score', 'Playmaker_Score', 'Rebounder_Score', 'Defensive Player_Score']
            
            # Needs to have scores
            if all(col in df.columns for col in score_cols):
                temp_df = df[df['SEASON'] == target_season_sel].copy() # Compare in same season
                temp_df = temp_df[temp_df['PLAYER_ID'] != target_data['PLAYER_ID']]
                
                # Calculate Distance
                dist = ((temp_df[score_cols] - target_data[score_cols])**2).sum(axis=1)**0.5
                temp_df['Similarity_Distance'] = dist
                
                closest = temp_df.sort_values('Similarity_Distance').head(5)
                
                st.markdown(f"**Top 5 Most Similar Players in {target_season_sel}:**")
                display_cols = ['PLAYER_NAME', 'Cluster', 'Tier', 'PTS', 'AST', 'REB', 'USG_PCT']
                st.table(closest[display_cols].set_index('PLAYER_NAME'))
            else:
                st.warning("Archetype scores missing from dataset.")

