import streamlit as st

def main():
    st.set_page_config(
        page_title="NBA AI Analytics Dashboard",
        page_icon="🏀",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("🏀 Welcome to the NBA AI & Analytics Dashboard")
    
    st.markdown("""
    ### Experience the Fast-Paced World of the NBA Through Data
    The **National Basketball Association (NBA)** is the premier professional basketball league in the world, featuring the highest level of athletic 
    talent, strategic gameplay, and exhilarating highlights. But beyond the dunks and buzzer-beaters lies a massive, complex network of **data**. 
    Every dribble, pass, shot, and defensive stop is quantified. 
    
    ---

    ### 🌟 What can you do with this project?
    This full-stack analytics platform bridges the gap between raw basketball statistics and actionable intelligence. Using advanced **data science** 
    and **machine learning**, this dashboard provides a deep dive into player capabilities and predictive insights. 
    
    Here is what you can explore using the sidebar:
    
    - **🏀 Player Stats & Comparisons**: Compare two players head-to-head with per-game stats and percentile radar charts, league-wide or within an inferred position.
    - **📊 Player Clusters**: Every player-season is assigned an archetype (Scorer, Playmaker, Rebounder, Defensive Player) from standardized stats, then **K-Means** splits each archetype into Elite / Very Good / Average tiers. Includes a similar-player finder.
    - **⭐ All-Star Predictions**: A hand-weighted **Impact Score** (PIE, team win %, per-game production, net rating) builds 6-guard / 6-forward / 3-center rosters for each conference and season.
    - **🔮 Next Game Prediction**: An **XGBoost** model predicts which team wins a matchup from each team's season-to-date overall, home and road win percentages.
    - **📈 Team Insights**: Franchise win percentage over time, best and worst seasons, and championship history since 2000.
    - **🤖 MVP Predictions**: An **XGBoost** MVP model evaluated with leave-one-season-out cross-validation, with the top candidates for any season.

    ---
    🗣️ **Ready to tip off?** 
    Expand the sidebar on the left and select a page to start exploring the data!
    """)

if __name__ == "__main__":
    main()
