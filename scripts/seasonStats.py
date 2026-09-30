# Fills the player_stats table straight from seasonStats.csv
# (one row per player per club per season)
 
import os
import csv
import mysql.connector
from dotenv import load_dotenv
 
load_dotenv()
 
conn = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT")),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
)
cursor = conn.cursor()
 
STATS_CSV = "datasets/seasonStats.csv"
BATCH_SIZE = 1000
 
# CSV column -> (player_stats column, type)
STAT_COLUMNS = [
    ("MP", "appearances", int),
    ("Min", "minutes_played", int),
    ("Gls", "goals", int),
    ("Ast", "assists", int),
    ("PK", "penalty_scored", int),
    ("PKatt", "penalty_attempts", int),
    ("CrdY", "yellow_cards", int),
    ("CrdR", "red_cards", int),
    ("OG", "own_goals", int),
    ("shots", "shots_total", int),
    ("SoT", "shots_on_target", int),
    ("Crs", "crosses", int),
    ("Fls", "fouls_committed", int),
    ("Fld", "fouls_drawn", int),
    ("Off", "offsides", int),
    ("TklW", "tackles_won", int),
    ("Int", "interceptions", int),
    ("PPM", "points_per_match", float),
    ("+/-", "plus_minus", int),
    ("xg", "xg", float),
    ("xa", "xa", float),
    ("key_passes", "key_passes", int),
]
 
 
def to_number(value, kind):
    value = (value or "").strip().replace(",", "")  # "1,234" -> "1234"
    if value == "":
        return None
    return int(float(value)) if kind is int else float(value)
 
 
def get_existing_ids(query):
    cursor.execute(query)
    return {row[0] for row in cursor.fetchall()}
 
 
def get_club_seasons():
    cursor.execute("SELECT club_id, season_id FROM club_season")
    return set(cursor.fetchall())
 
 
def insert_player_stats():
    valid_players = get_existing_ids("SELECT player_id FROM player")
    valid_clubs = get_existing_ids("SELECT club_id FROM club")
    valid_seasons = get_existing_ids("SELECT season_id FROM season")
    club_seasons = get_club_seasons()
 
    rows = []
    seen = set()
    missing_player = missing_club = missing_season = duplicates = no_club_season = 0
 
    with open(STATS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            player_id = to_number(row["player_id"], int)
            club_id = to_number(row["club_id"], int)
            season_id = to_number(row["Season"], int)
 
            # Foreign key safety checks
            if player_id not in valid_players:
                missing_player += 1  # e.g. skipped earlier for no nation/position
                continue
            if club_id not in valid_clubs:
                missing_club += 1
                continue
            if season_id not in valid_seasons:
                missing_season += 1
                continue
 
            if (club_id, season_id) not in club_seasons:
                no_club_season += 1  # still inserted, just flagged
 
            # Same player/club/season twice in the CSV (e.g. loan and return)
            key = (player_id, club_id, season_id)
            if key in seen:
                duplicates += 1
            seen.add(key)
 
            stats = [to_number(row[csv_col], kind) for csv_col, _, kind in STAT_COLUMNS]
            rows.append((player_id, club_id, season_id, *stats))
 
    db_cols = ["player_id", "club_id", "season_id"] + [db_col for _, db_col, _ in STAT_COLUMNS]
    placeholders = ", ".join(["%s"] * len(db_cols))
    updates = ",\n                ".join(f"{c} = new.{c}" for c in db_cols[3:])
 
    sql = f"""
        INSERT INTO player_stats ({", ".join(db_cols)})
        VALUES ({placeholders}) AS new
            ON DUPLICATE KEY UPDATE
                {updates}
    """  # safe to re-run IF player_stats has UNIQUE (player_id, club_id, season_id)
 
    # Insert in batches so one giant statement doesn't hit MySQL's packet limit
    for i in range(0, len(rows), BATCH_SIZE):
        cursor.executemany(sql, rows[i:i + BATCH_SIZE])
    conn.commit()
 
    print(f"{len(rows)} stat rows inserted/updated")
    print(f"Skipped: {missing_player} player not in player table, "
          f"{missing_club} club not in club table, {missing_season} season not in season table")
    if duplicates:
        print(f"{duplicates} repeated player/club/season rows in the CSV")
    if no_club_season:
        print(f"{no_club_season} stat rows have no matching club_season row")
 
 
insert_player_stats()
 
cursor.close()
conn.close()
print("Done!")