# Fills the goalkeeper_stats table from the keeper stats CSV. Each row is linked
# to its player_stats row by looking up the stat_id for that player/club/season.
 
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
 
KEEPER_CSV = "datasets/goalkeeperStats.csv"
BATCH_SIZE = 1000
 
# CSV column -> goalkeeper_stats column
STAT_COLUMNS = [
    ("GA", "goals_conceded"),
    ("SoTA", "shots_on_target_against"),
    ("Saves", "saves"),
    ("CS", "clean_sheets"),
    ("PKatt_stats_keeper", "penalties_faced"),
    ("PKA", "penalty_conceded"),
    ("PKsv", "penalty_saved"),
    ("PKm", "penalty_missed"),
]
 
 
def to_int(value):
    value = (value or "").strip().replace(",", "")
    return int(float(value)) if value else None
 
 
def get_stat_ids():
    # (player_id, club_id, season_id) -> stat_id
    cursor.execute("SELECT stat_id, player_id, club_id, season_id FROM player_stats")
    return {(p, c, s): stat_id for stat_id, p, c, s in cursor.fetchall()}
 
 
def insert_goalkeeper_stats():
    stat_ids = get_stat_ids()
 
    rows = []
    used_stat_ids = set()
    no_stat_row = duplicates = 0
 
    with open(KEEPER_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (to_int(row["player_id"]), to_int(row["club_id"]), to_int(row["Season"]))
 
            # Find the matching player_stats row - no match means nothing to link to
            stat_id = stat_ids.get(key)
            if stat_id is None:
                no_stat_row += 1
                continue
 
            if stat_id in used_stat_ids:
                duplicates += 1  # same keeper/club/season twice, later row wins
            used_stat_ids.add(stat_id)
 
            stats = [to_int(row[csv_col]) for csv_col, _ in STAT_COLUMNS]
            rows.append((stat_id, *stats))
 
    db_cols = ["stat_id"] + [db_col for _, db_col in STAT_COLUMNS]
    placeholders = ", ".join(["%s"] * len(db_cols))
    updates = ",\n                ".join(f"{c} = new.{c}" for c in db_cols[1:])
 
    sql = f"""
        INSERT INTO goalkeeper_stats ({", ".join(db_cols)})
        VALUES ({placeholders}) AS new
            ON DUPLICATE KEY UPDATE
                {updates}
    """  # safe to re-run - stat_id is the primary key
 
    for i in range(0, len(rows), BATCH_SIZE):
        cursor.executemany(sql, rows[i:i + BATCH_SIZE])
    conn.commit()
 
    print(f"{len(rows)} goalkeeper stat rows inserted/updated")
    print(f"Skipped {no_stat_row} rows with no matching player_stats row")
    if duplicates:
        print(f"{duplicates} repeated keeper/club/season rows in the CSV")
 
 
insert_goalkeeper_stats()
 
cursor.close()
conn.close()
print("Done!")