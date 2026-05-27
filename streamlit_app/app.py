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
    
    - **🏀 Player Stats & Comparisons**: Dive deep into raw and percentile-based statistics. Compare players head-to-head across different roles (Scorers, Playmakers, Defenders) intuitively.
    - **📊 Player Clusters**: Which players have exactly the same playstyle? We used un-supervised machine learning to group the entire league into unique behavioral clusters based on how they actually play, not just their positions.
    - **⭐ All-Star Predictions**: Who is trending to be an All-Star? Our ML models evaluate current stats against historical voting trends to predict future highly-acclaimed selections.
    - **🔮 Next Game Prediction**: Predict a player's performance in their upcoming matchup based on their recent momentum and the opponent's defensive vulnerabilities.
    - **📈 Team Insights**: Analyze how entire rosters stack up against each other in offensive flow and defensive solidity.
    - **🤖 Model Predictions & Methodology**: Go "under the hood" to see the precision of our Random Forest, XGBoost, and neural network algorithms.

    ---
    🗣️ **Ready to tip off?** 
    Expand the sidebar on the left and select a page to start exploring the data!
    """)

if __name__ == "__main__":
    main()
