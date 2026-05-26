import streamlit as st

def main():
    st.set_page_config(
        page_title="NBA Analytics Dashboard",
        page_icon="??",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("?? NBA Analytics Dashboard")
    
    st.markdown("""
    Welcome to the **NBA Analytics Dashboard**! 
    
    This application provides deep insights, statistics, and machine learning predictions for individual NBA players and teams.
    
    ### ?? Navigate through the pages in the sidebar to explore:
    - **?? Player Stats**: View and analyze individual player statistics.
    - **?? Team Insights**: Explore team performance and metrics.
    - **?? Model Predictions**: Check out our machine learning predictions for MVP, All-Stars, and Next Game performances.
    - **?? Player Clusters**: Discover player archetypes using unsupervised machine learning.
    - **?? About Project**: Learn more about the methodology, data pipeline, and models used in this project.
    
    ---
    *Data dynamically built utilizing advanced data pipelines and machine learning models.*
    """)

if __name__ == "__main__":
    main()
