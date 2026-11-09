import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from src.features import to_per_game
from src.paths import CLUSTERED_PLAYERS, PROCESSED_DIR, RAW_PLAYER_STATS

ID_COLS = ['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'SEASON', 'Cluster', 'Tier']

ARCHETYPE_FEATURES = {
    'Scorer': ['PTS', 'USG_PCT', 'TS_PCT'],
    'Playmaker': ['AST', 'AST_PCT'],
    'Rebounder': ['REB', 'REB_PCT'],
    'Defensive Player': ['STL', 'BLK', 'INV_DEF_RATING'],
}


def load_and_filter_data(file_path=RAW_PLAYER_STATS):
    # Counting stats in the raw file are season totals; archetypes compare per-game production.
    df = to_per_game(pd.read_csv(file_path))
    initial_len = len(df)

    # Filtering rules: min 20 games played, min 15 minutes per game, min 12% usage
    df = df[(df['GP'] >= 20) & (df['MIN'] >= 15.0) & (df['USG_PCT'] >= 0.12)].copy()

    print(f"Filtered dataset from {initial_len} to {len(df)} players (Removed low usage/minutes).")
    return df


def assign_archetypes(df):
    """
    Groups players into Scorer, Playmaker, Rebounder, Defensive Player based on
    whichever standardized stat profile is their strongest relative trait.
    This is a rule (highest composite score wins), not a clustering algorithm.
    """
    # Invert DEF_RATING so a lower rating gives a higher score
    df['INV_DEF_RATING'] = df['DEF_RATING'].max() - df['DEF_RATING']

    all_features = sorted({col for cols in ARCHETYPE_FEATURES.values() for col in cols})
    scaled = StandardScaler().fit_transform(df[all_features].fillna(0))
    scaled_df = pd.DataFrame(scaled, columns=all_features, index=df.index)

    for archetype, cols in ARCHETYPE_FEATURES.items():
        df[f'{archetype}_Score'] = scaled_df[cols].mean(axis=1)

    score_cols = [f'{k}_Score' for k in ARCHETYPE_FEATURES]
    df['Cluster'] = df[score_cols].idxmax(axis=1).str.replace('_Score', '')
    return df


def assign_tiers(group_df, archetype_name):
    """
    Uses 1D K-Means clustering to find Elite, Very Good, and Average tiers
    within the specific archetype group.
    """
    score_col = f'{archetype_name}_Score'

    if len(group_df) < 3:
        group_df['Tier'] = 'Average'
        return group_df

    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    group_df['KMeans_Label'] = kmeans.fit_predict(group_df[[score_col]])

    # Order the clusters by their mean score to assign ordinal tiers
    centers = group_df.groupby('KMeans_Label')[score_col].mean().sort_values()
    tier_mapping = {
        centers.index[0]: 'Average',
        centers.index[1]: 'Very Good',
        centers.index[2]: 'Elite',
    }
    group_df['Tier'] = group_df['KMeans_Label'].map(tier_mapping)
    return group_df.drop(columns=['KMeans_Label'])


def run_clustering_pipeline():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    df = assign_archetypes(load_and_filter_data())

    final_dfs = []
    for cluster in ARCHETYPE_FEATURES:
        cluster_df = df[df['Cluster'] == cluster].copy()
        if cluster_df.empty:
            continue

        cluster_df = assign_tiers(cluster_df, cluster)
        cluster_df = cluster_df[ID_COLS + [c for c in cluster_df.columns if c not in ID_COLS]]

        save_path = PROCESSED_DIR / (cluster.lower().replace(' ', '_') + '_data.csv')
        cluster_df.to_csv(save_path, index=False)
        print(f"Saved {len(cluster_df)} players to {save_path}")
        final_dfs.append(cluster_df)

        elite_players = cluster_df[cluster_df['Tier'] == 'Elite']
        print(f" -> {cluster} Elite Count: {len(elite_players)}")
        if len(elite_players) > 0:
            print(f" -> Example Elites: {', '.join(elite_players['PLAYER_NAME'].head(3).tolist())}")
        print("-" * 50)

    master_df = pd.concat(final_dfs, ignore_index=True)
    master_df.to_csv(CLUSTERED_PLAYERS, index=False)
    print(f"Saved master clustered dataset to {CLUSTERED_PLAYERS}")


if __name__ == '__main__':
    run_clustering_pipeline()
