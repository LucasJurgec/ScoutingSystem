# Fills the club_season table: one row per club per season they appear in
# seasonStats.csv. There are no second-tier leagues in the data (no Championship
# etc.), so a club appearing in a season means it was in its country's top league.
# The club's country comes from Transfermarkt's player_valuations.csv
# (player_club_domestic_competition_id for each current_club_id, e.g. GB1 = England),
# and the league is whichever league has that nation_code.
 
import os
import csv
from collections import Counter, defaultdict
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
VALUATIONS_CSV = "datasets/player_valuations.csv"
 
# Transfermarkt competition id -> nation_code (FBref style, matches nation table)
COMPETITION_NATION = {
    "GB1": "ENG",   # Premier League
    "ES1": "ESP",   # La Liga
    "IT1": "ITA",   # Serie A
    "L1": "GER",    # Bundesliga
    "FR1": "FRA",   # Ligue 1
    "NL1": "NED",   # Eredivisie
    "BE1": "BEL",   # Belgian Pro League
    "TR1": "TUR",   # Super Lig
    "PO1": "POR",   # Liga Portugal
    "SC1": "SCO",   # Scottish Premiership
    "RU1": "RUS",   # Russian Premier Liga
    "UKR1": "UKR",  # Ukrainian Premier Liga
    "GR1": "GRE",   # Greek Super League
    "DK1": "DEN",   # Danish Superliga
}
 
 
def get_existing_ids(query):
    cursor.execute(query)
    return {row[0] for row in cursor.fetchall()}
 
 
def get_league_ids():
    # competition id -> league_id, by matching on the league's nation_code
    cursor.execute("SELECT league_id, nation_code FROM league")
    by_nation = {}
    for league_id, nation_code in cursor.fetchall():
        nation_code = nation_code.strip().upper()
        if nation_code in by_nation:
            print(f"WARNING: more than one league for {nation_code} - "
                  f"using league_id {by_nation[nation_code]}")
            continue
        by_nation[nation_code] = league_id
 
    league_ids = {}
    for comp_id, nation_code in COMPETITION_NATION.items():
        if nation_code in by_nation:
            league_ids[comp_id] = by_nation[nation_code]
    return league_ids
 
 
def get_club_leagues(league_ids):
    # club_id -> league_id, using the competition listed for that club in the
    # valuations file. If a club has more than one, take the most common.
    comp_counts = defaultdict(Counter)
    with open(VALUATIONS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            club_id = (row["current_club_id"] or "").strip()
            comp_id = (row["player_club_domestic_competition_id"] or "").strip()
            if club_id and comp_id:
                comp_counts[int(float(club_id))][comp_id] += 1
 
    club_leagues = {}
    for club_id, counts in comp_counts.items():
        comp_id = counts.most_common(1)[0][0]
        if comp_id in league_ids:
            club_leagues[club_id] = league_ids[comp_id]
    return club_leagues
 
 
def insert_club_seasons():
    valid_clubs = get_existing_ids("SELECT club_id FROM club")
    valid_seasons = get_existing_ids("SELECT season_id FROM season")
    league_ids = get_league_ids()
    club_leagues = get_club_leagues(league_ids)
 
    pairs = set()  # every distinct (club_id, season_id) in the stats
    with open(STATS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            club_id = (row["club_id"] or "").strip()
            season_id = (row["Season"] or "").strip()
            if club_id and season_id:
                pairs.add((int(float(club_id)), int(season_id)))
 
    rows = []
    unknown_clubs = set()
    unknown_seasons = set()
    no_league = set()
 
    for club_id, season_id in sorted(pairs):
        if club_id not in valid_clubs:
            unknown_clubs.add(club_id)
            continue
        if season_id not in valid_seasons:
            unknown_seasons.add(season_id)
            continue
        league_id = club_leagues.get(club_id)
        if league_id is None:
            no_league.add(club_id)
            continue
        rows.append((club_id, season_id, league_id))
 
    cursor.executemany("""
        INSERT INTO club_season (club_id, season_id, league_id)
        VALUES (%s, %s, %s) AS new
            ON DUPLICATE KEY UPDATE
                league_id = new.league_id
        """, rows)  # safe to re-run
 
    conn.commit()
 
    print(f"{len(rows)} club seasons inserted/updated "
          f"({len({c for c, _, _ in rows})} clubs, {len({s for _, s, _ in rows})} seasons)")
    if unknown_clubs:
        print(f"Club ids not in club table: {sorted(unknown_clubs)}")
    if unknown_seasons:
        print(f"Season ids not in season table: {sorted(unknown_seasons)}")
    if no_league:
        print(f"Clubs with no matching league (not in valuations, or league not in league table): "
              f"{sorted(no_league)}")
 
 
insert_club_seasons()
 
cursor.close()
conn.close()
print("Done!")