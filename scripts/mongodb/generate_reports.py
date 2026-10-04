"""
Generate one scouting report per player, as a strengths/weaknesses profile.
 
Two tiers:
  - FULL report: players in the top-5 leagues in the top 25% by latest market
    value. Each gets a summary line plus strengths and weaknesses derived from
    their real 2025-26 stats (per-90 rates and ratios, not just totals), phrased
    like a scout. The vector search runs on these.
  - PLACEHOLDER: every other player gets an empty document so a user can write
    the report from the website later.
 
Output: data/reports/reports.json
No embeddings / no MongoDB here - read the text first, then we embed + load.
 
Run from the repo root:  python scripts/generate_reports.py
"""
import os
import json
import math
import random
from datetime import date
 
import mysql.connector
from dotenv import load_dotenv
 
SEASON_ID = 2526
TOP_MV_FRACTION = 0.25
MAX_STRENGTHS = 3
MAX_WEAKNESSES = 2
MIN_MINUTES = 450            # below this, the per-90 sample is too small to trust
OUTPUT = "data/reports/reports.json"
random.seed(42)
 
TOP5_LEAGUE_IDS = []        # fill in if known, e.g. [10, 11, 12, 13, 14]
TOP5_LEAGUE_NAME_KEYWORDS = [
    "premier league", "laliga", "la liga", "serie a", "bundesliga", "ligue 1",
]
 
 
def classify_position(general, advanced):
    a = (advanced or "").upper().strip()
    g = (general or "").lower().strip()
    if a == "GK" or "keeper" in g or g == "goalkeeper":
        return "GK"
    if a in {"CB", "LB", "RB", "LWB", "RWB", "DF"} or "def" in g or "back" in g:
        return "DEF"
    if a in {"DM", "CM", "AM", "CDM", "CAM", "LM", "RM", "MF"} or "mid" in g:
        return "MID"
    if a in {"ST", "CF", "SS", "LW", "RW", "FW"} or any(k in g for k in ("att", "forward", "strik", "wing")):
        return "FWD"
    return "UNKNOWN"
 
 
def pick(opts):
    return random.choice(opts)
 
 
def age_from_dob(dob):
    if not dob:
        return None
    return 2026 - dob.year - ((3, 1) < (dob.month, dob.day))
 
 
def per90(value, minutes):
    if not minutes:
        return 0.0
    return float(value or 0) / float(minutes) * 90
 
 
def evaluate_outfield(p, s):
    mins = s.get("minutes_played", 0) or 0
    bucket = p["bucket"]
    strengths, weaknesses = [], []
 
    g = s.get("goals", 0) or 0
    a = s.get("assists", 0) or 0
    xg = s.get("xg", 0) or 0
    xa = s.get("xa", 0) or 0
    shots = s.get("shots_total", 0) or 0
    sot = s.get("shots_on_target", 0) or 0
    kp = s.get("key_passes", 0) or 0
    tk = (s.get("tackles_won", 0) or 0) + (s.get("interceptions", 0) or 0)
    crosses = s.get("crosses", 0) or 0
    fouls_c = s.get("fouls_committed", 0) or 0
    fouls_d = s.get("fouls_drawn", 0) or 0
    offs = s.get("offsides", 0) or 0
    yc = s.get("yellow_cards", 0) or 0
    rc = s.get("red_cards", 0) or 0
    og = s.get("own_goals", 0) or 0
    pen_sc = s.get("penalty_scored", 0) or 0
    pen_at = s.get("penalty_attempts", 0) or 0
    apps = s.get("appearances", 0) or 0
 
    g90, a90, kp90 = per90(g, mins), per90(a, mins), per90(kp, mins)
    tk90, cr90 = per90(tk, mins), per90(crosses, mins)
    fc90, fd90, off90 = per90(fouls_c, mins), per90(fouls_d, mins), per90(offs, mins)
    sh90, yc90 = per90(shots, mins), per90(yc, mins)
    goal_thresh = {"FWD": 0.55, "MID": 0.30, "DEF": 0.12}.get(bucket, 0.3)
 
    if g90 >= goal_thresh:
        strengths.append((g90, pick([
            f"Prolific in front of goal ({g} in the league this season)",
            f"A genuine goal threat, netting {g}",
            f"Consistent output in the final third with {g} goals",
        ])))
    if g - xg >= 3:
        strengths.append((g - xg, pick([
            "A clinical finisher who regularly beats his expected goals",
            "Takes his chances ruthlessly, well above his xG",
            "Ice-cold in front of goal, outscoring what the numbers predict",
        ])))
    elif g - xg <= -3:
        weaknesses.append((abs(g - xg), pick([
            "Wasteful in front of goal, underperforming his xG",
            "Leaves chances on the table; his finishing lags his xG",
            "Profligate at times, not converting the chances he gets",
        ])))
    if shots >= 25 and sot / shots <= 0.30:
        weaknesses.append((shots, pick([
            "Shot selection is loose, with too many efforts off target",
            "Lacks precision in front of goal; low shots-on-target rate",
        ])))
    elif shots >= 20 and sot / shots >= 0.52:
        strengths.append((sot / shots, "Accurate striker of the ball, hits the target consistently"))
    if sh90 >= 2.5 and g90 < 0.25:
        weaknesses.append((sh90, "Shoots often but with little to show for it"))
    if g >= 6 and pen_sc / max(g, 1) >= 0.40:
        weaknesses.append((pen_sc, "Goal tally leans heavily on penalties"))
    if pen_at >= 4 and pen_sc / pen_at <= 0.60:
        weaknesses.append((pen_at, "Unreliable from the penalty spot"))
 
    if a90 >= 0.30:
        strengths.append((a90, pick([
            f"A prolific provider with {a} assists",
            f"Creates goals for others regularly ({a} assists)",
        ])))
    if kp90 >= 2.0:
        strengths.append((kp90, pick([
            "A creative hub who carves out chances",
            "Excellent vision and range of passing",
            "Constantly manufacturing openings for teammates",
        ])))
    if a - xa >= 2:
        strengths.append((a - xa, "His end product beats his underlying numbers"))
    elif xa >= 3 and a - xa <= -2:
        weaknesses.append((abs(a - xa), "Creates plenty but the assists haven't followed"))
 
    def_thresh = {"DEF": 5.0, "MID": 4.0, "FWD": 2.2}.get(bucket, 4.0)
    if tk90 >= def_thresh:
        strengths.append((tk90, pick([
            "A tenacious ball-winner who reads the game well",
            "Breaks up play tirelessly; strong defensive output",
            "Aggressive and effective out of possession",
        ])))
    if bucket == "DEF" and tk90 < 2.5 and mins >= MIN_MINUTES:
        weaknesses.append((2.5 - tk90, "Passive out of possession for a defender"))
    if fc90 >= 1.8:
        weaknesses.append((fc90, "Gives away a lot of fouls, overcommitting at times"))
 
    if rc >= 2 or yc90 >= 0.35:
        weaknesses.append((yc + rc * 2, pick([
            "Discipline is a concern given his booking record",
            "Prone to needless bookings",
            "Hot-headed; his card count is a liability",
        ])))
    elif apps >= 15 and yc90 <= 0.08:
        strengths.append((1.0, "Disciplined, rarely caught out of position or in the book"))
 
    if fd90 >= 1.5:
        strengths.append((fd90, "Press-resistant and tough to dispossess, drawing fouls in key areas"))
    if bucket == "FWD" and off90 >= 0.8:
        weaknesses.append((off90, "Timing of his runs needs work; caught offside too often"))
    if cr90 >= 2.5 and bucket in ("DEF", "MID", "FWD"):
        if a90 < 0.15:
            weaknesses.append((cr90, "Crosses in volume but with limited quality"))
        else:
            strengths.append((cr90, "A real crossing threat from wide"))
    if apps >= 33:
        strengths.append((apps, "An ever-present; durable and available week in, week out"))
    if og >= 2:
        weaknesses.append((og, "The odd costly lapse, including own goals"))
 
    return strengths, weaknesses
 
 
def evaluate_gk(p, gk):
    strengths, weaknesses = [], []
    saves = gk.get("saves", 0) or 0
    cs = gk.get("clean_sheets", 0) or 0
    conceded = gk.get("goals_conceded", 0) or 0
    psaved = gk.get("penalty_saved", 0) or 0
    faced = saves + conceded
    save_rate = saves / faced if faced else 0
 
    if cs >= 12:
        strengths.append((cs, pick([
            f"Racks up clean sheets ({cs} this season)",
            f"A commanding presence, shutting out opponents {cs} times",
        ])))
    elif cs <= 3:
        weaknesses.append((5, "Clean sheets have been hard to come by"))
    if save_rate >= 0.72 and faced >= 40:
        strengths.append((save_rate, "An excellent shot-stopper with a high save percentage"))
    elif save_rate <= 0.62 and faced >= 40:
        weaknesses.append((1 - save_rate, "Shot-stopping has been below par this season"))
    if psaved >= 2:
        strengths.append((psaved, f"A penalty specialist, saving {psaved} spot-kicks"))
    if conceded >= 45:
        weaknesses.append((conceded, "Picked the ball out of his net a lot"))
    return strengths, weaknesses
 
 
def fallback_weakness(bucket):
    return pick({
        "FWD": ["Contributes little outside the box", "Limited involvement in build-up play"],
        "MID": ["End product could be higher for a player in his role", "Can drift out of games"],
        "DEF": ["Offers little going forward", "Distribution from the back can be rushed"],
        "GK": ["Distribution with his feet is a work in progress", "Can be tested on crosses"],
    }.get(bucket, ["Consistency is the next step"]))
 
 
def fallback_strength(bucket):
    return pick({
        "FWD": ["A willing runner who stretches defences", "Gets into good positions"],
        "MID": ["A tidy operator who keeps the ball moving", "Reliable in possession"],
        "DEF": ["Positionally sound and dependable", "A steady presence at the back"],
        "GK": ["A calm presence in goal", "Reliable with the routine saves"],
    }.get(bucket, ["A solid contributor"]))
 
 
def build_report(p, s, gk):
    name, club = p["name"], (p["club"] or "his club")
    pos, age = p["position_advanced"] or p["bucket"], p["age"]
    who = f"{name}, a {age}-year-old {pos} at {club}" if age else f"{name}, a {pos} at {club}"
 
    s = s or {}
    apps = s.get("appearances", 0) or 0
    if p["bucket"] != "GK" and (apps < 5 or (s.get("minutes_played", 0) or 0) < MIN_MINUTES):
        summary = f"{who}. Limited minutes in 2025-26, so this profile is provisional - one to monitor."
        return summary, [], [], summary
 
    if p["bucket"] == "GK":
        strengths, weaknesses = evaluate_gk(p, gk or {})
    else:
        strengths, weaknesses = evaluate_outfield(p, s)
 
    strengths.sort(key=lambda x: x[0], reverse=True)
    weaknesses.sort(key=lambda x: x[0], reverse=True)
    strengths = [t for _, t in strengths][:MAX_STRENGTHS]
    weaknesses = [t for _, t in weaknesses][:MAX_WEAKNESSES]
 
    if not strengths:
        strengths = [fallback_strength(p["bucket"])]
    if not weaknesses:
        weaknesses = [fallback_weakness(p["bucket"])]
 
    summary = f"{who}."
    text = summary + "\n\nStrengths:\n" + "\n".join(f"- {t}" for t in strengths)
    text += "\n\nWeaknesses:\n" + "\n".join(f"- {t}" for t in weaknesses)
    return summary, strengths, weaknesses, text
 
 
def connect():
    load_dotenv()
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"), user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"), database=os.getenv("DB_NAME"),
    )
 
 
def resolve_top5_leagues(cur):
    if TOP5_LEAGUE_IDS:
        return set(TOP5_LEAGUE_IDS)
    cur.execute("SELECT league_id, league_name FROM league")
    ids, matched = set(), []
    for lid, lname in cur.fetchall():
        if any(k in (lname or "").lower() for k in TOP5_LEAGUE_NAME_KEYWORDS):
            ids.add(lid); matched.append(lname)
    print("Top-5 leagues matched by name:", matched)
    return ids
 
 
def get_players(cur):
    cur.execute("""
        SELECT p.player_id, p.first_name, p.last_name, p.date_of_birth,
               pos.position_general, pos.position_advanced, c.club_name
        FROM player p
        LEFT JOIN position pos ON pos.position_id = p.position_id
        LEFT JOIN club c ON c.club_id = p.club_id
    """)
    players = {}
    for pid, fn, ln, dob, pg, pa, club in cur.fetchall():
        players[pid] = {
            "player_id": pid, "name": f"{fn} {ln}".strip(), "age": age_from_dob(dob),
            "position_advanced": pa, "bucket": classify_position(pg, pa), "club": club,
        }
    return players
 
 
def get_latest_mv(cur):
    cur.execute("""
        SELECT mv.player_id, mv.market_value FROM market_value mv
        JOIN (SELECT player_id, MAX(value_date) latest FROM market_value GROUP BY player_id) x
          ON mv.player_id = x.player_id AND mv.value_date = x.latest
    """)
    return {pid: (v or 0) for pid, v in cur.fetchall()}
 
 
def get_top5_players(cur, league_ids):
    if not league_ids:
        return set()
    fmt = ",".join(["%s"] * len(league_ids))
    cur.execute(f"""
        SELECT DISTINCT ps.player_id FROM player_stats ps
        JOIN club_season cs ON cs.club_id = ps.club_id AND cs.season_id = ps.season_id
        WHERE ps.season_id = %s AND cs.league_id IN ({fmt})
    """, (SEASON_ID, *league_ids))
    return {r[0] for r in cur.fetchall()}
 
 
def get_outfield_stats(cur):
    cols = ["appearances", "minutes_played", "goals", "assists", "penalty_scored",
            "penalty_attempts", "yellow_cards", "red_cards", "own_goals", "shots_total",
            "shots_on_target", "crosses", "fouls_committed", "fouls_drawn", "offsides",
            "tackles_won", "interceptions", "key_passes", "xg", "xa"]
    cur.execute(f"""
        SELECT player_id, {", ".join("SUM(" + c + ")" for c in cols)}
        FROM player_stats WHERE season_id = %s GROUP BY player_id
    """, (SEASON_ID,))
    out = {}
    for row in cur.fetchall():
        out[row[0]] = {c: (row[i + 1] or 0) for i, c in enumerate(cols)}
    return out
 
 
def get_gk_stats(cur):
    cur.execute("""
        SELECT ps.player_id, SUM(gk.saves), SUM(gk.clean_sheets),
               SUM(gk.goals_conceded), SUM(gk.penalty_saved)
        FROM player_stats ps JOIN goalkeeper_stats gk ON gk.stat_id = ps.stat_id
        WHERE ps.season_id = %s GROUP BY ps.player_id
    """, (SEASON_ID,))
    return {pid: {"saves": sv or 0, "clean_sheets": cs or 0,
                  "goals_conceded": gc or 0, "penalty_saved": ps or 0}
            for pid, sv, cs, gc, ps in cur.fetchall()}
 
 
def main():
    conn = connect(); cur = conn.cursor()
    league_ids = resolve_top5_leagues(cur)
    players = get_players(cur)
    mv = get_latest_mv(cur)
    top5 = get_top5_players(cur, league_ids)
    outfield = get_outfield_stats(cur)
    gk = get_gk_stats(cur)
    cur.close(); conn.close()
 
    top5_sorted = sorted(top5, key=lambda pid: mv.get(pid, 0), reverse=True)
    full_set = set(top5_sorted[:math.ceil(len(top5_sorted) * TOP_MV_FRACTION)])
 
    docs, written, unknown = [], 0, 0
    for pid, p in players.items():
        if p["bucket"] == "UNKNOWN":
            unknown += 1
        if pid in full_set:
            summary, strengths, weaknesses, text = build_report(p, outfield.get(pid), gk.get(pid))
            docs.append({"player_id": pid, "summary": summary, "strengths": strengths,
                         "weaknesses": weaknesses, "report_text": text,
                         "last_updated": date.today().isoformat(), "source": "generated"})
            written += 1
        else:
            docs.append({"player_id": pid, "summary": "", "strengths": [], "weaknesses": [],
                         "report_text": "", "last_updated": date.today().isoformat(),
                         "source": "placeholder"})
 
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)
 
    print(f"\n{len(docs)} documents -> {OUTPUT}")
    print(f"  {written} full reports, {len(docs) - written} placeholders")
    if unknown:
        print(f"  NOTE: {unknown} players had an unrecognised position - tell Lucas to map them.")
    print("\n--- samples ---")
    for d in [d for d in docs if d["source"] == "generated"][:4]:
        print("\n" + d["report_text"])
 
 
if __name__ == "__main__":
    main()