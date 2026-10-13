# This will be used to find similar players based on their stats
# It will only include 25/26 season stats and the player must be in the top 5 leagues
# All stats will be included, including the scouting reports using the vector index
# K-NN will be used

import os
from dotenv import load_dotenv
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
import mysql.connector
from database import _mysql_config
from database import get_connection

load_dotenv()

SEASON = 2526
TOP5 = [8, 9, 10, 12, 15] # league_id for top 5 leagues
MIN_MINUTES = 900

FEATURES = {
    "Defender": [
        "xg",
        "xa",     
        "key_passes",
        "tackles_won",
        "interceptions",
        "fouls_committed",
        "fouls_drawn",
        "yellow_cards"
    ],
    "Midfielder": [
        "goals",
        "assists",
        "xg",
        "xa",
        "shots_total",
        "key_passes", 
        "interceptions",
        "tackles_won",
        "fouls_committed",
        "fouls_drawn",
        "crosses",
        "yellow_cards"
    ],
    "Attacker": [
        "goals",
        "assists",
        "xg",
        "xa",
        "shots_total",
        "shots_on_target",
        "key_passes", 
        "interceptions",
        "tackles_won",
        "offsides",
        "fouls_committed",
        "fouls_drawn",
        "crosses",
        "yellow_cards"
    ]
}

models = {}

def load_players():
    all_stats = sorted({col for cols in FEATURES.values() for col in cols})
    stat_cols = ", ".join(f"SUM(ps.{s}) AS {s}" for s in all_stats)
    placeholders = ", ".join(["%s"] * len(TOP5))

    query = f"""
        SELECT ps.player_id,
               p.first_name, p.last_name,
               pos.position_general,
               MAX(cs.league_id) AS league_id,
               SUM(ps.minutes_played) AS minutes,
               {stat_cols}
        FROM player_stats ps
        JOIN player p        ON ps.player_id = p.player_id
        JOIN position pos    ON p.position_id = pos.position_id
        JOIN club_season cs  ON ps.club_id = cs.club_id AND ps.season_id = cs.season_id
        WHERE ps.season_id = %s
          AND cs.league_id IN ({placeholders})
          AND pos.position_general != 'Goalkeeper'
        GROUP BY ps.player_id, p.first_name, p.last_name, pos.position_general
        HAVING SUM(ps.minutes_played) >= %s
    """
    params = [SEASON, *TOP5, MIN_MINUTES]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params)
    df = pd.DataFrame(cursor.fetchall())
    cursor.close()
    conn.close()

    df["name"] = (df["first_name"].fillna("") + " " + df["last_name"].fillna("")).str.strip()
    df[all_stats] = df[all_stats].astype(float)
    df["minutes"] = df["minutes"].astype(float)
    for stat in all_stats:
        df[stat + "_p90"] = df[stat] / df["minutes"] * 90

    return df

def build_models(df):
    # Scale each position group's stats and build its k-NN index
    models.clear()
    for position, group in df.groupby("position_general"):
        group = group.reset_index(drop=True)

        # the per-90 columns this position uses
        cols = [stat + "_p90" for stat in FEATURES[position]]

        X = StandardScaler().fit_transform(group[cols])
        knn = NearestNeighbors(metric="cosine").fit(X)

        models[position] = (group, X, knn)

    print("Loaded players per position:", {pos: len(g) for pos, (g, _, _) in models.items()})

def find_similar(player_id, n=5):
    for group, X, knn in models.values():
        match = group.index[group["player_id"] == player_id]
        if len(match) == 0:
            continue  # not in this position group, try the next

        i = match[0]
        k = min(n + 1, len(group))  # +1 because the player matches itself
        distances, indices = knn.kneighbors(X[i].reshape(1, -1), n_neighbors=k)

        results = group.iloc[indices[0]].copy()
        results["similarity"] = ((1 - distances[0]) * 100).round(1)
        results = results[results["player_id"] != player_id].head(n)

        return results[["player_id", "name", "position_general", "league_id", "similarity"]].to_dict("records")

    return None

# checks if a player is eligible for comparison
def is_eligible(player_id):
    return any((group["player_id"] == player_id).any() for group, _, _ in models.values())

# refreshes the model from the database, useful if the database has been updated
def refresh():
    build_models(load_players())