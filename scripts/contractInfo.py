# Fills the contract_information table for every player with a current club.
#
#   contract_start  -> latest transfer INTO their current club (transfer table),
#                      falling back to 1 July of their first season at the club
#                      (player_stats) for academy players with no transfer
#   contract_expiry -> Transfermarkt player.csv (contract_expiration_date)
#   weekly_wage     -> GENERATED from latest market value
#   release_clause  -> GENERATED: always for La Liga (it's required by Spanish
#                      law), ~25% of players elsewhere, otherwise NULL
#
# random.seed() means the generated values are the same every run.
 
import os
import csv
import random
from datetime import date
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
BATCH_SIZE = 1000
random.seed(42)
 
WAGE_SHARE = 0.12          # yearly wage is roughly 12% of market value...
WAGE_NOISE = (0.7, 1.3)    # ...give or take 30%
MIN_WEEKLY_WAGE = 1500
DEFAULT_MARKET_VALUE = 500_000     # for players with no valuation at all
OTHER_LEAGUE_CLAUSE_CHANCE = 0.25
 
 
def round_to(value, step):
    return int(round(value / step) * step)
 
 
def get_current_players():
    cursor.execute("SELECT player_id, club_id FROM player WHERE club_id IS NOT NULL")
    return dict(cursor.fetchall())
 
 
def get_contract_starts():
    # Latest transfer into the player's current club
    cursor.execute("""
        SELECT t.player_id, MAX(t.transfer_date)
        FROM transfer t
        JOIN player p ON p.player_id = t.player_id AND t.to_club_id = p.club_id
        GROUP BY t.player_id
    """)
    starts = dict(cursor.fetchall())
 
    # Fallback: first season they have stats at their current club
    cursor.execute("""
        SELECT ps.player_id, MIN(s.start_year)
        FROM player_stats ps
        JOIN player p ON p.player_id = ps.player_id AND ps.club_id = p.club_id
        JOIN season s ON s.season_id = ps.season_id
        GROUP BY ps.player_id
    """)
    fallbacks = {pid: date(int(year), 7, 1) for pid, year in cursor.fetchall()}
    return starts, fallbacks
 
 
def get_latest_market_values():
    cursor.execute("""
        SELECT mv.player_id, mv.market_value
        FROM market_value mv
        JOIN (SELECT player_id, MAX(value_date) AS latest
              FROM market_value GROUP BY player_id) x
          ON mv.player_id = x.player_id AND mv.value_date = x.latest
    """)
    return dict(cursor.fetchall())
 
 
def get_club_nations():
    # club_id -> nation_code of the league in their most recent club_season
    cursor.execute("""
        SELECT cs.club_id, cs.season_id, l.nation_code
        FROM club_season cs
        JOIN league l ON l.league_id = cs.league_id
    """)
    latest = {}
    for club_id, season_id, nation in cursor.fetchall():
        if club_id not in latest or season_id > latest[club_id][0]:
            latest[club_id] = (season_id, nation)
    return {club_id: nation for club_id, (_, nation) in latest.items()}
 
 
def get_expiry_dates():
    expiries = {}
    with open(PLAYER_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            value = (row["contract_expiration_date"] or "").strip()[:10]
            if value:
                expiries[int(row["player_id"])] = date.fromisoformat(value)
    return expiries
 
 
def make_wage(market_value):
    yearly = market_value * WAGE_SHARE * random.uniform(*WAGE_NOISE)
    weekly = max(yearly / 52, MIN_WEEKLY_WAGE)
    return round_to(weekly, 500)
 
 
def make_release_clause(market_value, nation):
    if nation == "ESP":
        return round_to(market_value * random.uniform(3, 6), 1_000_000)
    if random.random() < OTHER_LEAGUE_CLAUSE_CHANCE:
        return round_to(market_value * random.uniform(1.5, 3), 1_000_000)
    return None
 
 
def insert_contracts():
    players = get_current_players()
    starts, fallbacks = get_contract_starts()
    values = get_latest_market_values()
    club_nations = get_club_nations()
    expiries = get_expiry_dates()
 
    rows = []
    from_transfer = from_stats = no_start = no_expiry = bad_dates = no_value = 0
 
    for player_id, club_id in sorted(players.items()):  # sorted so random values are stable
        start = starts.get(player_id)
        if start:
            from_transfer += 1
        else:
            start = fallbacks.get(player_id)
            if start:
                from_stats += 1
            else:
                no_start += 1
 
        expiry = expiries.get(player_id)
        if expiry is None:
            no_expiry += 1
 
        if start and expiry and start >= expiry:
            bad_dates += 1
            start = None  # don't store a contract that ends before it starts
 
        market_value = values.get(player_id)
        if market_value is None:
            no_value += 1
            market_value = DEFAULT_MARKET_VALUE
 
        rows.append((
            player_id,
            start.isoformat() if start else None,
            expiry.isoformat() if expiry else None,
            make_wage(market_value),
            make_release_clause(market_value, club_nations.get(club_id)),
        ))
 
    sql = """
        INSERT INTO contract_information (player_id, contract_start, contract_expiry,
                                          weekly_wage, release_clause)
        VALUES (%s, %s, %s, %s, %s) AS new
            ON DUPLICATE KEY UPDATE
                contract_start = new.contract_start,
                contract_expiry = new.contract_expiry,
                weekly_wage = new.weekly_wage,
                release_clause = new.release_clause
    """  # safe to re-run - player_id is the primary key
 
    for i in range(0, len(rows), BATCH_SIZE):
        cursor.executemany(sql, rows[i:i + BATCH_SIZE])
    conn.commit()
 
    print(f"{len(rows)} contracts inserted/updated")
    print(f"contract_start: {from_transfer} from transfers, {from_stats} from first season at club, "
          f"{no_start} unknown")
    print(f"{no_expiry} with no expiry date, {bad_dates} had start after expiry (start set to NULL)")
    print(f"{no_value} had no market value (used {DEFAULT_MARKET_VALUE:,} for wage/clause)")
 
 
insert_contracts()
 
cursor.close()
conn.close()
print("Done!")