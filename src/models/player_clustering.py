import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import os
import warnings
warnings.filterwarnings('ignore')

def load_and_filter_data(file_path):
    df = pd.read_csv(file_path)
    initial_len = len(df)
    
    # Avoid players with lower minutes and slim to none usage
    # Filtering rules: min 20 Games Played, min 15 Minutes, min 12% Usage
    df = df[(df['GP'] >= 20) & (df['MIN'] >= 15.0) & (df['USG_PCT'] >= 0.12)].copy()
    
    print(f"Filtered dataset from {initial_len} to {len(df)} players (Removed low usage/minutes).")
    return df

def assign_archetypes(df):
    """
    Groups players into Scorer, Playmaker, Rebounder, Defensive Player
    based on whichever standardized stat profile is their strongest relative trait.
    """
    scaler = StandardScaler()
    
    # Invert DEF_RATING so a lower rating gives a higher score
    df['INV_DEF_RATING'] = df['DEF_RATING'].max() - df['DEF_RATING']
    
    # Define features for each archetype
    features = {
        'Scorer': ['PTS', 'USG_PCT', 'TS_PCT'],
        'Playmaker': ['AST', 'AST_PCT'],
        'Rebounder': ['REB', 'REB_PCT'],
        'Defensive Player': ['STL', 'BLK', 'INV_DEF_RATING']
    }
    
    # Scale features across the whole dataset
    all_features = list(set([item for sublist in features.values() for item in sublist]))
    scaled_data = scaler.fit_transform(df[all_features].fillna(0))
    scaled_df = pd.DataFrame(scaled_data, columns=all_features, index=df.index)
    
    # Composite score for each archetype
    archetypes = list(features.keys())
    for archetype, cols in features.items():
        df[f'{archetype}_Score'] = scaled_df[cols].mean(axis=1)
        
    # Assign cluster based on highest relative score
    score_cols = [f'{k}_Score' for k in archetypes]
    df['Cluster'] = df[score_cols].idxmax(axis=1).str.replace('_Score', '')
    
    return df

def assign_tiers(group_df, archetype_name):
    """
    Uses 1D K-Means clustering to naturally find Elite, Very Good, and Average tiers 
    within the specific archetype cluster.
    """
    score_col = f'{archetype_name}_Score'
    
    # Need at least 3 players to do K=3 clustering
    if len(group_df) < 3:
        group_df['Tier'] = 'Average'
        return group_df
        
    kmeans = KMeans(n_clusters=3, random_state=42)
    labels = kmeans.fit_predict(group_df[[score_col]])
    group_df['KMeans_Label'] = labels
    
    # Get cluster centers to determine the ordinal rank of the clusters
    centers = group_df.groupby('KMeans_Label')[score_col].mean().sort_values()
    
    tier_mapping = {
        centers.index[0]: 'Average',    # Lowest cluster center
        centers.index[1]: 'Very Good',  # Middle cluster center
        centers.index[2]: 'Elite'       # Highest cluster center
    }
    
    group_df['Tier'] = group_df['KMeans_Label'].map(tier_mapping)
    group_df = group_df.drop(columns=['KMeans_Label'])
    return group_df

def run_clustering_pipeline():
    raw_data_path = 'data/raw/nba_player_stats.csv'
    processed_dir = 'data/processed'
    os.makedirs(processed_dir, exist_ok=True)
    
    # 1. Load and Filter
    df = load_and_filter_data(raw_data_path)
    
    # 2. Assign base Archetypes (Clusters)
    df = assign_archetypes(df)
    
    # 3. Assign internal Tiers using K-Means and split into distinct datasets
    final_dfs = []
    
    for cluster in ['Scorer', 'Playmaker', 'Rebounder', 'Defensive Player']:
        cluster_df = df[df['Cluster'] == cluster].copy()
        
        if len(cluster_df) > 0:
            cluster_df = assign_tiers(cluster_df, cluster)
            
            # Save to separate dataset
            filename = cluster.lower().replace(' ', '_') + '_data.csv'
            save_path = os.path.join(processed_dir, filename)
            
            # Reorder columns to make Tier and Cluster visible
            cols = ['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'SEASON', 'Cluster', 'Tier'] + \
                   [c for c in cluster_df.columns if c not in ['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'SEASON', 'Cluster', 'Tier']]
            cluster_df = cluster_df[cols]
            
            cluster_df.to_csv(save_path, index=False)
            print(f"Saved {len(cluster_df)} players to {save_path}")
            
            final_dfs.append(cluster_df)
            
            # Print a quick summary of the Elite tier
            elite_players = cluster_df[cluster_df['Tier'] == 'Elite']
            print(f" -> {cluster} Elite Count: {len(elite_players)}")
            if len(elite_players) > 0:
                print(f" -> Example Elites: {', '.join(elite_players['PLAYER_NAME'].head(3).tolist())}")
            print("-" * 50)

    # Note: We can also save a master clustered dataset
    master_df = pd.concat(final_dfs, ignore_index=True)
    master_save_path = os.path.join(processed_dir, 'clustered_players_master.csv')
    master_df.to_csv(master_save_path, index=False)
    print(f"Saved master clustered dataset to {master_save_path}")

if __name__ == '__main__':
    run_clustering_pipeline()
