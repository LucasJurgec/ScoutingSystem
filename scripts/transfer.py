
# Fills the transfer table from Transfermarkt's transfers.csv.
#
# The data has no loan flag (loans, free transfers and loan returns all have
# fee 0), so loans are worked out from the pattern of moves:
#   A -> B, then the player's NEXT move is B -> A for no fee within 2 years
#   => A -> B was a Loan, with loan_end_date = the date of the return.
# The return row itself is not inserted - it's represented by loan_end_date.
 
import os
import csv
from datetime import date
from collections import defaultdict
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
 
TRANSFERS_CSV = "datasets/transfers.csv"
BATCH_SIZE = 1000
MAX_LOAN_DAYS = 2 * 365 + 30  # a return later than this isn't treated as a loan
 
# Transfermarkt placeholder "clubs" - not real moves between clubs
PLACEHOLDER_CLUBS = {"Retired", "Without Club", "Unknown", "Career break"}
 
 
def to_int(value):
    value = (value or "").strip().replace(",", "")
    if value in ("", "nan", "?", "-"):
        return None
    return int(float(value))
 
 
def get_existing_ids(query):
    cursor.execute(query)
    return {row[0] for row in cursor.fetchall()}
 
 
def load_moves(valid_players):
    # player_id -> list of moves, sorted by date
    moves = defaultdict(list)
    missing_player = 0
 
    with open(TRANSFERS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            player_id = to_int(row["player_id"])
            if player_id not in valid_players:
                missing_player += 1
                continue
 
            moves[player_id].append({
                "date": date.fromisoformat(row["transfer_date"].strip()[:10]),
                "from_id": to_int(row["from_club_id"]),
                "to_id": to_int(row["to_club_id"]),
                "from_name": (row["from_club_name"] or "").strip(),
                "to_name": (row["to_club_name"] or "").strip(),
                "fee": to_int(row["transfer_fee"]),
                "type": None,
                "loan_end": None,
                "is_return": False,
            })
 
    for player_moves in moves.values():
        player_moves.sort(key=lambda m: m["date"])
    return moves, missing_player
 
 
def classify(player_moves):
    for i, move in enumerate(player_moves):
        if move["is_return"]:
            continue
 
        # Loan check: is the very next move straight back, for free, soon after?
        if i + 1 < len(player_moves):
            nxt = player_moves[i + 1]
            if (nxt["from_id"] == move["to_id"]
                    and nxt["to_id"] == move["from_id"]
                    and not nxt["fee"]
                    and (nxt["date"] - move["date"]).days <= MAX_LOAN_DAYS):
                move["type"] = "Loan"
                move["loan_end"] = nxt["date"]
                nxt["is_return"] = True
                continue
 
        if move["fee"] is None:
            move["type"] = "Permanent"  # fee unknown
        elif move["fee"] > 0:
            move["type"] = "Permanent"
        else:
            move["type"] = "Free"
 
 
def insert_transfers():
    valid_players = get_existing_ids("SELECT player_id FROM player")
    valid_clubs = get_existing_ids("SELECT club_id FROM club")
    today = date.today()
 
    moves, missing_player = load_moves(valid_players)
 
    rows = []
    loan_returns = future = placeholder = missing_club = 0
    type_counts = {"Loan": 0, "Free": 0, "Permanent": 0}
 
    for player_id, player_moves in moves.items():
        classify(player_moves)
 
        for m in player_moves:
            if m["is_return"]:
                loan_returns += 1  # stored as loan_end_date on the loan instead
                continue
            if m["date"] > today:
                future += 1  # scheduled, hasn't happened yet
                continue
            if m["from_name"] in PLACEHOLDER_CLUBS or m["to_name"] in PLACEHOLDER_CLUBS:
                placeholder += 1
                continue
            if m["from_id"] not in valid_clubs or m["to_id"] not in valid_clubs:
                missing_club += 1
                continue
 
            type_counts[m["type"]] += 1
            rows.append((
                player_id,
                m["from_id"],
                m["to_id"],
                m["type"],
                m["date"].isoformat(),
                m["fee"],
                m["loan_end"].isoformat() if m["loan_end"] else None,
            ))
 
    sql = """
        INSERT INTO transfer (player_id, from_club_id, to_club_id, transfer_type,
                              transfer_date, transfer_fee, loan_end_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s) AS new
            ON DUPLICATE KEY UPDATE
                from_club_id = new.from_club_id,
                transfer_type = new.transfer_type,
                transfer_fee = new.transfer_fee,
                loan_end_date = new.loan_end_date
    """  # safe to re-run IF transfer has UNIQUE (player_id, transfer_date, to_club_id)
 
    for i in range(0, len(rows), BATCH_SIZE):
        cursor.executemany(sql, rows[i:i + BATCH_SIZE])
    conn.commit()
 
    print(f"{len(rows)} transfers inserted/updated: {type_counts}")
    print(f"Not inserted: {loan_returns} loan returns (stored as loan_end_date), "
          f"{future} future-dated, {placeholder} to/from Retired/Without Club, "
          f"{missing_club} club not in club table")
    print(f"Skipped {missing_player} rows for players not in the player table")
 
 
insert_transfers()
 
cursor.close()
conn.close()
print("Done!")