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

load_dotenv()

SEASON = 2526
TOP5 = [8, 9, 10, 12, 15] # league_id for top 5 leagues
MIN_MINUTES = 900

FEATURES = {
    "DF": [
        "xg",
        "xa",     
        "key_passes",
        "tackles_won",
        "interceptions",
        "fouls_committed",
        "fouls_drawn",
        "yellow_cards"
    ],
    "MF": [
        "goals",
        "assists",
        "xg",
        "xa",
        "shots",
        "key_passes", 
        "interceptions",
        "tackles_won",
        "fouls_committed",
        "fouls_drawn",
        "crosses",
        "yellow_cards"
    ],
    "FW": [
        "goals",
        "assists",
        "xg",
        "xa",
        "shots",
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
    # Load eligible outfield players and compute per-90 stats
    all_stats = sorted({col for cols in FEATURES.values() for col in cols})
    stat_cols = ", ".join(f"ps.{s}" for s in all_stats)
    placeholders = ", ".join(["%s"] * len(TOP5))

    query = f"""
        SELECT ps.player_id,
               p.first_name, p.last_name,
               pos.position_general,
               ps.league_id, ps.minutes,
               {stat_cols}
        FROM player_stats ps
        JOIN players p   ON ps.player_id = p.player_id
        JOIN positions pos ON p.position_id = pos.position_id
        WHERE ps.season_id = %s
          AND ps.league_id IN ({placeholders})
          AND ps.minutes >= %s
          AND pos.position_general != 'goalkeeper'
    """
    params = [SEASON, *TOP5, MIN_MINUTES]

    conn = mysql.connector.connect(**_mysql_config())
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params)
    df = pd.DataFrame(cursor.fetchall())
    cursor.close()
    conn.close()

    # build a single display name
    df["name"] = df["first_name"] + " " + df["last_name"]

    # convert raw counting stats to per-90: stat / minutes * 90
    df[all_stats] = df[all_stats].astype(float)
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