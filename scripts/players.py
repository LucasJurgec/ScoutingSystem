# Fills the player table from player.csv (Transfermarkt), with nation_code taken
# from each player's most recent season in seasonStats.csv, and a status
# (Active / Free Agent / Retired) worked out from last_season and club
 
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
 
PLAYER_CSV = "datasets/players.csv"
STATS_CSV = "datasets/seasonStats.csv"
 
# Start year of the most recent season in the data (2025 = 2025/26).
# A player whose last_season is more than one season before this counts as retired.
CURRENT_SEASON = 2025
 
# Transfermarkt sub_position -> position_advanced in the position table
SUB_POSITION_MAP = {
    "Goalkeeper": "GK",
    "Right-Back": "RB",
    "Left-Back": "LB",
    "Centre-Back": "CB",
    "Defensive Midfield": "DM",
    "Central Midfield": "CM",
    "Attacking Midfield": "AM",
    "Right Midfield": "RM",
    "Left Midfield": "LM",
    "Right Winger": "RW",
    "Left Winger": "LW",
    "Centre-Forward": "ST",
    "Second Striker": "ST",
}
 
# Fallback if sub_position is blank - use the general position instead
GENERAL_POSITION_MAP = {
    "Goalkeeper": "GK",
    "Defender": "CB",
    "Midfield": "CM",
    "Attack": "ST",
}
 
 
def blank_to_none(value):
    value = value.strip() if value else ""
    return value if value else None
 
 
def get_position_ids():
    # Look the ids up instead of hardcoding 13-24, so it survives a table rebuild
    cursor.execute("SELECT position_id, position_advanced FROM position")
    return {abbr.strip(): pos_id for pos_id, abbr in cursor.fetchall()}
 
 
def get_existing_ids(query):
    cursor.execute(query)
    return {row[0] for row in cursor.fetchall()}
 
 
def get_latest_nations():
    # player_id -> nation from their most recent season
    latest = {}  # player_id -> (season, nation)
    with open(STATS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            nation = blank_to_none(row["Nation"])
            if nation is None:
                continue  # don't let a blank nation overwrite a real one
            player_id = int(row["player_id"])
            season = int(row["Season"])
            if player_id not in latest or season > latest[player_id][0]:
                latest[player_id] = (season, nation)
    return {pid: nation for pid, (season, nation) in latest.items()}
 
 
def get_status(last_season, club_id):
    if last_season is not None and last_season < CURRENT_SEASON - 1:
        return "Retired"
    if club_id is None:
        return "Free Agent"
    return "Active"
 
 
def insert_players():
    position_ids = get_position_ids()
    valid_clubs = get_existing_ids("SELECT club_id FROM club")
    valid_nations = get_existing_ids("SELECT nation_code FROM nation")
    nations = get_latest_nations()
 
    rows = []
    missing_nation = missing_position = 0
    status_counts = {"Active": 0, "Free Agent": 0, "Retired": 0}
    unknown_nations = set()
    unknown_clubs = set()
    unknown_positions = set()
 
    with open(PLAYER_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            player_id = int(row["player_id"])
 
            # Only load players that actually have season stats
            if player_id not in nations:
                continue
 
            # Position (NOT NULL + FK, so skip the player if it doesn't map)
            abbr = SUB_POSITION_MAP.get(row["sub_position"]) or GENERAL_POSITION_MAP.get(row["position"])
            position_id = position_ids.get(abbr)
            if position_id is None:
                missing_position += 1
                unknown_positions.add((row["position"], row["sub_position"]))
                continue
 
            # Nation (NOT NULL + FK, so skip the player if it's not in the nation table)
            nation_code = nations[player_id]
            if nation_code not in valid_nations:
                missing_nation += 1
                unknown_nations.add(nation_code)
                continue
 
            # Club (nullable - NULL means no current club)
            club_id = blank_to_none(row["current_club_id"])
            club_id = int(club_id) if club_id else None
            if club_id is not None and club_id not in valid_clubs:
                unknown_clubs.add(club_id)
                club_id = None
 
            # Status
            last_season = blank_to_none(row["last_season"])
            last_season = int(float(last_season)) if last_season else None
            status = get_status(last_season, club_id)
            if status == "Retired":
                club_id = None  # retired players shouldn't be listed at their old club
            status_counts[status] += 1
 
            dob = blank_to_none(row["date_of_birth"])
            dob = dob[:10] if dob else None  # "1978-06-09 00:00:00" -> "1978-06-09"
 
            height = blank_to_none(row["height_in_cm"])
            height = int(float(height)) if height else None
 
            rows.append((
                player_id,
                blank_to_none(row["first_name"]),
                blank_to_none(row["last_name"]),
                dob,
                blank_to_none(row["image_url"]),
                height,
                position_id,
                club_id,
                nation_code,
                status,
            ))
 
    cursor.executemany("""
        INSERT INTO player (player_id, first_name, last_name, date_of_birth, player_img,
                            height, position_id, club_id, nation_code, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) AS new
            ON DUPLICATE KEY UPDATE
                first_name = new.first_name,
                last_name = new.last_name,
                date_of_birth = new.date_of_birth,
                player_img = new.player_img,
                height = new.height,
                position_id = new.position_id,
                club_id = new.club_id,
                nation_code = new.nation_code,
                status = new.status
        """, rows)  # safe to re-run
 
    conn.commit()
 
    print(f"{len(rows)} players inserted/updated")
    print(f"Status: {status_counts}")
    print(f"Skipped {missing_nation} with no valid nation, {missing_position} with no position")
 
    if unknown_nations:
        print(f"Nation codes not in nation table: {sorted(unknown_nations)}")
    if unknown_positions:
        print(f"Unmapped (position, sub_position): {sorted(unknown_positions)}")
    if unknown_clubs:
        print(f"Club ids not in club table (set to NULL): {sorted(unknown_clubs)}")
 
 
insert_players()
 
cursor.close()
conn.close()
print("Done!")
