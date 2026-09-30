# Fills the market_value table from Transfermarkt's player_valuations.csv
# (one row per valuation per player)
 
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
 
VALUATIONS_CSV = "datasets/player_valuations.csv"
BATCH_SIZE = 1000
 
# Set to a date like "2017-07-01" to only keep valuations from the 17/18 season
# onwards (matching your stats). None keeps every valuation.
MIN_DATE = None
 
 
def get_existing_ids(query):
    cursor.execute(query)
    return {row[0] for row in cursor.fetchall()}
 
 
def insert_market_values():
    valid_players = get_existing_ids("SELECT player_id FROM player")
 
    values = {}  # (player_id, date) -> value, so a repeated row can't be added twice
    missing_player = bad_rows = too_old = 0
 
    with open(VALUATIONS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            player_id = (row["player_id"] or "").strip()
            date = (row["date"] or "").strip()[:10]  # handles "2020-01-20 00:00:00" too
            value = (row["market_value_in_eur"] or "").strip()
 
            if not player_id or not date or not value:
                bad_rows += 1
                continue
 
            player_id = int(float(player_id))
            if player_id not in valid_players:
                missing_player += 1
                continue
 
            if MIN_DATE and date < MIN_DATE:
                too_old += 1
                continue
 
            values[(player_id, date)] = int(float(value))
 
    rows = [(player_id, value, date) for (player_id, date), value in values.items()]
 
    sql = """
        INSERT INTO market_value (player_id, market_value, value_date)
        VALUES (%s, %s, %s) AS new
            ON DUPLICATE KEY UPDATE
                market_value = new.market_value
    """  # safe to re-run IF market_value has UNIQUE (player_id, value_date)
 
    for i in range(0, len(rows), BATCH_SIZE):
        cursor.executemany(sql, rows[i:i + BATCH_SIZE])
    conn.commit()
 
    print(f"{len(rows)} market values inserted/updated "
          f"across {len({p for p, _, _ in rows})} players")
    print(f"Skipped: {missing_player} player not in player table, {bad_rows} blank rows"
          + (f", {too_old} before {MIN_DATE}" if MIN_DATE else ""))
 
 
insert_market_values()
 
cursor.close()
conn.close()
print("Done!")