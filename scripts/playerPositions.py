# Fills the player_position table with each player's extra positions from the EA FC 27 dataset
 
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
 
POSITIONS_CSV = "datasets/EAFC_playerPositions.csv"
 
# EA position codes -> position_advanced in the position table
EA_POSITION_MAP = {
    "GK": "GK",
    "RB": "RB",
    "RWB": "RB",
    "LB": "LB",
    "LWB": "LB",
    "CB": "CB",
    "CDM": "DM",
    "CM": "CM",
    "CAM": "AM",
    "RM": "RM",
    "LM": "LM",
    "RW": "RW",
    "LW": "LW",
    "ST": "ST",
    "CF": "ST",
}
 
 
def get_position_ids():
    cursor.execute("SELECT position_id, position_advanced FROM position")
    return {abbr.strip(): pos_id for pos_id, abbr in cursor.fetchall()}
 
 
def get_player_main_positions():
    # player_id -> their main position_id (so we don't store it again as an extra)
    cursor.execute("SELECT player_id, position_id FROM player")
    return {player_id: pos_id for player_id, pos_id in cursor.fetchall()}
 
 
def insert_player_positions():
    position_ids = get_position_ids()
    main_positions = get_player_main_positions()
 
    rows = set()  # set so the same (player, position) pair can't be added twice
    missing_players = 0
    unknown_codes = set()
 
    with open(POSITIONS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            player_id = int(row["player_id"])
 
            # Safety check - player has to exist in the player table
            if player_id not in main_positions:
                missing_players += 1
                continue
 
            # EA's main position counts as an extra too if it differs from our
            # main (Transfermarkt) one, e.g. TM says RW but EA says CAM.
            # Alternates are space separated ("CDM CAM CB"); commas also handled.
            alternates = (row["alternate_positions"] or "").replace(",", " ").split()
            codes = [row["position"] or ""] + alternates
 
            for code in codes:
                code = code.strip().upper()
                if not code:
                    continue
 
                abbr = EA_POSITION_MAP.get(code)
                position_id = position_ids.get(abbr)
                if position_id is None:
                    unknown_codes.add(code)
                    continue
 
                if position_id == main_positions[player_id]:
                    continue  # already stored as their main position
 
                rows.add((player_id, position_id))
 
    cursor.executemany("""
        INSERT INTO player_position (player_id, position_id)
        VALUES (%s, %s) AS new
            ON DUPLICATE KEY UPDATE
                position_id = new.position_id
        """, list(rows))  # safe to re-run
 
    conn.commit()
 
    players_with_extras = len({pid for pid, _ in rows})
    print(f"{len(rows)} extra positions inserted/updated across {players_with_extras} players")
    print(f"Skipped {missing_players} rows with a player_id not in the player table")
    if unknown_codes:
        print(f"Unmapped EA position codes: {sorted(unknown_codes)}")
 
 
insert_player_positions()
 
cursor.close()
conn.close()
print("Done!")