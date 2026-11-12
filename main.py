import os
import json
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from database import get_connection, get_reports_collection
from starlette.middleware.sessions import SessionMiddleware
from adminLogin import router as admin_router
import SimilarPlayerModel as sp
import csv, io
from datetime import datetime
from fastapi.responses import FileResponse

sp.refresh()  # load data + build the k-NN models once at startup
 
app = FastAPI(title="Scouting System API")

app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET"), max_age=60 * 60 * 8)
 
origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000",
).split(",")
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)
 
def run_query(sql, params=(), one=False):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute(sql, params)
        result = cursor.fetchone() if one else cursor.fetchall()
        cursor.close()
        return result
    finally:
        conn.close()
 
 
# The most recent season that has league data, used for "current" club/league
LATEST_SEASON = "(SELECT MAX(season_id) FROM club_season)"
 
@app.get("/")
def read_root():
    return {"message": "Scouting System API is running"}
 
 
@app.get("/health")
def health():
    status = {}
    try:
        row = run_query("SELECT COUNT(*) AS n FROM player", one=True)
        status["mysql"] = f"ok ({row['n']} players)"
    except Exception as e:
        status["mysql"] = f"error: {e}"
    try:
        count = get_reports_collection().count_documents({})
        status["mongodb"] = f"ok ({count} reports)"
    except Exception as e:
        status["mongodb"] = f"error: {e}"
    return status
 
 
# players
 
@app.get("/players")
def get_players(
    search: str = Query(None),
    nation_code: str = Query(None),
    club_id: int = Query(None),
    league_id: int = Query(None),
    position: str = Query(None),          # Goalkeeper / Defender / Midfielder / Attacker
    status: str = Query(None),            # Active / Free Agent / Retired
    sort: str = Query("value"),           # value / name
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    query = """
        SELECT
            p.player_id, p.first_name, p.last_name, p.player_img, p.status,
            TIMESTAMPDIFF(YEAR, p.date_of_birth, CURDATE()) AS age,
            pos.position_general, pos.position_advanced,
            c.club_id, c.club_name, c.club_logo,
            n.nation_code, n.nation_name, n.nation_flag,
            (SELECT mv.market_value FROM market_value mv
             WHERE mv.player_id = p.player_id
             ORDER BY mv.value_date DESC LIMIT 1) AS market_value
        FROM player p
        JOIN position pos ON p.position_id = pos.position_id
        LEFT JOIN club c  ON p.club_id = c.club_id      -- LEFT so free agents/retired still show
        JOIN nation n     ON p.nation_code = n.nation_code
        WHERE 1=1
    """
    params = []
 
    if search:
        # CONCAT_WS skips a NULL first_name, so "Saka" and "Bukayo Saka" both work
        query += " AND CONCAT_WS(' ', p.first_name, p.last_name) LIKE %s"
        params.append(f"%{search}%")
    if nation_code:
        query += " AND p.nation_code = %s"
        params.append(nation_code.upper())
    if club_id:
        query += " AND p.club_id = %s"
        params.append(club_id)
    if league_id:
        query += f""" AND p.club_id IN (
            SELECT club_id FROM club_season
            WHERE league_id = %s AND season_id = {LATEST_SEASON})"""
        params.append(league_id)
    if position:
        query += " AND pos.position_general = %s"
        params.append(position)
    if status:
        query += " AND p.status = %s"
        params.append(status)
 
    # whitelisted, never put user input straight into ORDER BY
    if sort == "name":
        query += " ORDER BY p.last_name ASC, p.first_name ASC"
    else:
        query += " ORDER BY market_value DESC, p.last_name ASC"
 
    query += " LIMIT %s OFFSET %s"
    params.extend([limit, offset])
 
    return run_query(query, params)
 
 
@app.get("/players/{player_id}")
def get_player(player_id: int):
    # --- core info ---
    player = run_query(f"""
        SELECT
            p.player_id, p.first_name, p.last_name, p.date_of_birth,
            TIMESTAMPDIFF(YEAR, p.date_of_birth, CURDATE()) AS age,
            p.height, p.player_img, p.status,
            pos.position_general, pos.position_advanced,
            c.club_id, c.club_name, c.club_logo,
            n.nation_code, n.nation_name, n.nation_flag,
            (SELECT l.league_name
             FROM club_season cs JOIN league l ON cs.league_id = l.league_id
             WHERE cs.club_id = p.club_id
             ORDER BY cs.season_id DESC LIMIT 1) AS league_name
        FROM player p
        JOIN position pos ON p.position_id = pos.position_id
        LEFT JOIN club c  ON p.club_id = c.club_id
        JOIN nation n     ON p.nation_code = n.nation_code
        WHERE p.player_id = %s
    """, (player_id,), one=True)
 
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
 
    # --- all positions they can play (junction table) ---
    positions = run_query("""
        SELECT pos.position_advanced
        FROM player_position pp
        JOIN position pos ON pp.position_id = pos.position_id
        WHERE pp.player_id = %s
    """, (player_id,))
    player["positions"] = [r["position_advanced"] for r in positions if r["position_advanced"]]
 
    # --- season stats (one row per season per club, GK columns NULL for outfielders) ---
    player["stats"] = run_query("""
        SELECT
            ps.*,
            s.season_name, s.start_year,
            c.club_name, c.club_logo,
            gk.goals_conceded, gk.shots_on_target_against, gk.saves,
            gk.clean_sheets, gk.penalties_faced, gk.penalty_conceded,
            gk.penalty_saved, gk.penalty_missed
        FROM player_stats ps
        JOIN season s ON ps.season_id = s.season_id
        JOIN club c   ON ps.club_id = c.club_id
        LEFT JOIN goalkeeper_stats gk ON ps.stat_id = gk.stat_id
        WHERE ps.player_id = %s
        ORDER BY s.start_year ASC
    """, (player_id,))
 
    # --- market value history (for the line chart) ---
    player["market_values"] = run_query("""
        SELECT value_date, market_value
        FROM market_value
        WHERE player_id = %s
        ORDER BY value_date ASC
    """, (player_id,))
    player["market_value"] = (
        player["market_values"][-1]["market_value"] if player["market_values"] else None
    )
 
    return player
 
 
@app.get("/players/{player_id}/contract")
def get_contract(player_id: int):
    """Structured contract columns + the semi-structured contract_data JSON.
    Returns null if there's no contract info on file for this player."""
    contract = run_query("""
        SELECT contract_start, contract_expiry, weekly_wage, release_clause, contract_data
        FROM contract_information
        WHERE player_id = %s
    """, (player_id,), one=True)
 
    if contract and contract["contract_data"]:
        data = contract["contract_data"]
        if isinstance(data, (bytes, bytearray)):
            data = data.decode()
        contract["contract_data"] = json.loads(data) if isinstance(data, str) else data
        add_club_names(contract["contract_data"])
    return contract
 
 
def add_club_names(contract_data):
    """Sell-on / buy-back clauses store club ids. Look up the names so the
    frontend can say "15% to Ajax" instead of "15% to club 610"."""
    if not isinstance(contract_data, dict):
        return
    clauses = [c for c in contract_data.get("clauses") or [] if isinstance(c, dict)]
    id_keys = ("from_club_id", "club_id")
    club_ids = {c[k] for c in clauses for k in id_keys if c.get(k)}
    if not club_ids:
        return
    placeholders = ", ".join(["%s"] * len(club_ids))
    rows = run_query(
        f"SELECT club_id, club_name FROM club WHERE club_id IN ({placeholders})",
        tuple(club_ids),
    )
    names = {r["club_id"]: r["club_name"] for r in rows}
    for c in clauses:
        for k in id_keys:
            if c.get(k) in names:
                c[k.replace("_id", "_name")] = names[c[k]]   # from_club_id -> from_club_name
 
 
@app.get("/players/{player_id}/report")
def get_report(player_id: int):
    """Latest scouting report from MongoDB (unstructured). null if none exists."""
    try:
        return get_reports_collection().find_one(
            {"player_id": player_id},
            {"_id": 0, "embedding": 0},     # drop the ObjectId and the 384-number vector
            sort=[("last_updated", -1)],    # newest first if there are several
        )
    except Exception:
        raise HTTPException(status_code=503, detail="Scouting reports are unavailable right now")


@app.get("/players/{player_id}/transfers")
def get_transfers(player_id: int):
    return run_query("""
        SELECT
            t.transfer_id, t.transfer_date, t.transfer_fee,
            fc.club_name AS from_club_name, fc.club_logo AS from_club_logo,
            tc.club_name AS to_club_name,   tc.club_logo AS to_club_logo
        FROM transfer t
        LEFT JOIN club fc ON t.from_club_id = fc.club_id
        LEFT JOIN club tc ON t.to_club_id   = tc.club_id
        WHERE t.player_id = %s
        ORDER BY t.transfer_date DESC
    """, (player_id,))

# similarity model

@app.get("/players/{player_id}/similar")
def get_similar(player_id: int):
    results = sp.find_similar(player_id, n=5)
    if results is None:
        raise HTTPException(status_code=404, detail="No similar-player data for this player")
    return {"results": results}

def run_write(sql, params=()):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()          # pool connections don't autocommit
        affected = cursor.rowcount
        cursor.close()
        return affected
    finally:
        conn.close()


# shortlist

@app.get("/shortlist")
def get_shortlist():
    players = run_query("""
        SELECT
            p.player_id, p.first_name, p.last_name, p.player_img, p.status,
            TIMESTAMPDIFF(YEAR, p.date_of_birth, CURDATE()) AS age,
            pos.position_general, pos.position_advanced,
            c.club_id, c.club_name, c.club_logo,
            n.nation_code, n.nation_name, n.nation_flag,
            (SELECT mv.market_value FROM market_value mv
                WHERE mv.player_id = p.player_id
                ORDER BY mv.value_date DESC LIMIT 1) AS market_value,
            s.date_added AS added_at,
 
            -- latest season stats (structured)
            st.appearances, st.minutes, st.goals, st.assists,
            st.xg, st.xa, st.key_passes, st.clean_sheets,
 
            -- contract (structured columns + semi-structured JSON)
            ci.contract_expiry, ci.weekly_wage, ci.release_clause,
            JSON_LENGTH(ci.contract_data, '$.clauses') AS extra_clauses
        FROM shortlist s
        JOIN player p     ON s.player_id = p.player_id
        JOIN position pos ON p.position_id = pos.position_id
        LEFT JOIN club c  ON p.club_id = c.club_id
        JOIN nation n     ON p.nation_code = n.nation_code
 
        -- one row per player: sums across clubs if they moved mid-season,
        -- so a January transfer doesn't show up twice on the shortlist
        LEFT JOIN (
            SELECT ps.player_id,
                   SUM(ps.appearances)    AS appearances,
                   SUM(ps.minutes_played) AS minutes,
                   SUM(ps.goals)          AS goals,
                   SUM(ps.assists)        AS assists,
                   ROUND(SUM(ps.xg), 2)   AS xg,
                   ROUND(SUM(ps.xa), 2)   AS xa,
                   SUM(ps.key_passes)     AS key_passes,
                   SUM(gk.clean_sheets)   AS clean_sheets      -- NULL for outfielders
            FROM player_stats ps
            LEFT JOIN goalkeeper_stats gk ON gk.stat_id = ps.stat_id
            WHERE ps.season_id = (SELECT MAX(season_id) FROM player_stats)
              AND ps.player_id IN (SELECT player_id FROM shortlist)
            GROUP BY ps.player_id
        ) st ON st.player_id = p.player_id
 
        LEFT JOIN contract_information ci ON ci.player_id = p.player_id
        ORDER BY s.date_added DESC
    """)
 
    # scouting reports (unstructured, MongoDB) — one lookup for the whole list
    ids = [p["player_id"] for p in players]
    reports = {}
    if ids:
        try:
            reports = {
                r["player_id"]: r.get("last_updated")
                for r in get_reports_collection().find(
                    {"player_id": {"$in": ids}},
                    {"_id": 0, "player_id": 1, "last_updated": 1},
                )
            }
        except Exception as e:
            # Mongo being down shouldn't break the shortlist page
            print("Shortlist: scouting reports unavailable:", repr(e))
            reports = None
 
    for p in players:
        if reports is None:
            p["has_report"] = p["report_updated"] = None
        else:
            p["has_report"] = "Yes" if p["player_id"] in reports else "No"
            p["report_updated"] = reports.get(p["player_id"])
 
    return players

@app.get("/shortlist/{player_id}")
def is_shortlisted(player_id: int):
    row = run_query("SELECT 1 AS x FROM shortlist WHERE player_id = %s", (player_id,), one=True)
    return {"shortlisted": row is not None}


@app.post("/shortlist/{player_id}", status_code=201)
def add_to_shortlist(player_id: int):
    if not run_query("SELECT 1 AS x FROM player WHERE player_id = %s", (player_id,), one=True):
        raise HTTPException(status_code=404, detail="Player not found")
    run_write("""
        INSERT INTO shortlist (player_id, date_added) VALUES (%s, NOW())
        ON DUPLICATE KEY UPDATE date_added = date_added
    """, (player_id,))
    return {"shortlisted": True}


@app.delete("/shortlist/{player_id}")
def remove_from_shortlist(player_id: int):
    run_write("DELETE FROM shortlist WHERE player_id = %s", (player_id,))
    return {"shortlisted": False}
 
# chatbot
 
class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []   # [{"role": "user"|"assistant", "content": "..."}]
 
 
@app.post("/chat")
def chat(req: ChatRequest):
    # imported here so a chatbot problem (missing package, no API key)
    # never takes down the rest of the API
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message is empty")
    try:
        from chatbot import ask
    except Exception as e:                         # missing package, bad import, etc.
        print("Chatbot failed to load:", repr(e))
        raise HTTPException(status_code=500, detail=f"Chatbot failed to load: {e}")
    from chatbot import AllModelsFailed
    debug = os.getenv("CHAT_DEBUG", "1") == "1"
    try:
        return ask(req.message, req.history)
    except RuntimeError as e:                      # e.g. no API keys set
        raise HTTPException(status_code=500, detail=str(e))
    except AllModelsFailed as e:
        busy = all(any(k in err.lower() for k in ("429", "503", "529", "resource_exhausted",
                                                  "unavailable", "overloaded", "high demand", "rate limit"))
                   for _, err in e.errors)
        if debug:
            # show every model's error so you can see e.g. Mistral's real problem
            raise HTTPException(status_code=503 if busy else 500,
                                detail={"message": "Every model failed", "errors": [f"{m}: {err}" for m, err in e.errors]})
        if busy:
            raise HTTPException(status_code=503, detail="The AI models are busy right now. Try again in a minute.")
        raise HTTPException(status_code=500, detail="Something went wrong answering that question.")
    except Exception as e:
        import traceback; traceback.print_exc()
        text = str(e)
        if "Recursion limit" in text:
            raise HTTPException(status_code=500, detail="The assistant couldn't work that one out. Try rephrasing the question.")
        if debug:
            raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {text[:500]}")
        raise HTTPException(status_code=500, detail="Something went wrong answering that question.")
 
 
# filter dropdowns
 
@app.get("/nations")
def get_nations():
    # only nations that actually have players, keeps the dropdown short
    return run_query("""
        SELECT nation_code, nation_name, nation_flag
        FROM nation
        WHERE nation_code IN (SELECT DISTINCT nation_code FROM player)
        ORDER BY nation_name ASC
    """)
 
 
@app.get("/clubs")
def get_clubs():
    # clubs in the most recent season, with the league they're in
    return run_query(f"""
        SELECT c.club_id, c.club_name, c.club_logo, l.league_id, l.league_name
        FROM club_season cs
        JOIN club c   ON cs.club_id = c.club_id
        JOIN league l ON cs.league_id = l.league_id
        WHERE cs.season_id = {LATEST_SEASON}
        ORDER BY c.club_name ASC
    """)
 
 
@app.get("/leagues")
def get_leagues():
    return run_query(f"""
        SELECT DISTINCT l.league_id, l.league_name, l.nation_code
        FROM club_season cs
        JOIN league l ON cs.league_id = l.league_id
        WHERE cs.season_id = {LATEST_SEASON}
        ORDER BY l.league_name ASC
    """)


# league summary
LEAGUE_SUMMARY_SQL = f"""
WITH stats_season AS (
    SELECT MAX(season_id) AS sid FROM player_stats
),
current_season AS (
    SELECT {LATEST_SEASON} AS sid
),
squad AS (
    SELECT
        cs.league_id,
        c.club_id,
        c.club_name,
        CONCAT_WS(' ', p.first_name, p.last_name) AS player_name,
        TIMESTAMPDIFF(YEAR, p.date_of_birth, CURDATE()) AS age,
        (SELECT mv.market_value FROM market_value mv
         WHERE mv.player_id = p.player_id
         ORDER BY mv.value_date DESC LIMIT 1) AS market_value,
        COALESCE((SELECT SUM(ps.goals) FROM player_stats ps
                  WHERE ps.player_id = p.player_id
                    AND ps.season_id = (SELECT sid FROM stats_season)), 0) AS goals,
        COALESCE((SELECT SUM(ps.assists) FROM player_stats ps
                  WHERE ps.player_id = p.player_id
                    AND ps.season_id = (SELECT sid FROM stats_season)), 0) AS assists
    FROM club_season cs
    JOIN club c   ON cs.club_id = c.club_id
    JOIN player p ON p.club_id = c.club_id
    WHERE cs.season_id = (SELECT sid FROM current_season)
      AND (%s IS NULL OR cs.league_id = %s)
),
ranked AS (
    SELECT squad.*,
        ROW_NUMBER() OVER (PARTITION BY club_id ORDER BY market_value DESC)          AS mv_rank,
        ROW_NUMBER() OVER (PARTITION BY club_id ORDER BY goals DESC, market_value DESC)   AS goal_rank,
        ROW_NUMBER() OVER (PARTITION BY club_id ORDER BY assists DESC, market_value DESC) AS assist_rank
    FROM squad
)
SELECT
    club_name,
    COUNT(*)                                            AS squad_size,
    ROUND(AVG(age), 1)                                  AS avg_age,
    ROUND(AVG(market_value))                            AS avg_market_value,
    MAX(market_value)                                   AS top_market_value,
    MAX(CASE WHEN mv_rank = 1 THEN player_name END)     AS top_value_player,
    SUM(goals)                                          AS total_goals,
    MAX(CASE WHEN goal_rank = 1 THEN player_name END)   AS top_scorer,
    MAX(CASE WHEN goal_rank = 1 THEN goals END)         AS top_scorer_goals,
    MAX(CASE WHEN assist_rank = 1 THEN player_name END) AS top_assister,
    MAX(CASE WHEN assist_rank = 1 THEN assists END)     AS top_assister_assists
FROM ranked
GROUP BY club_id, club_name
ORDER BY avg_market_value DESC
"""

def build_league_summary(league_id=None):
    return run_query(LEAGUE_SUMMARY_SQL, (league_id, league_id))

@app.get("/reports/league-summary")
def league_summary(league_id: int = Query(None)):
    return build_league_summary(league_id)

REPORTS_DIR = os.getenv("REPORTS_DIR", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

CSV_COLUMNS = [
    ("club_name", "Team"), ("squad_size", "Squad size"), ("avg_age", "Avg age"),
    ("avg_market_value", "Avg market value"), ("top_market_value", "Top market value"),
    ("top_value_player", "Top value player"), ("total_goals", "Total goals"),
    ("top_scorer", "Top scorer"), ("top_scorer_goals", "Top scorer goals"),
    ("top_assister", "Top assister"), ("top_assister_assists", "Top assister assists"),
]

def rows_to_csv(rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([label for _, label in CSV_COLUMNS])
    for r in rows:
        w.writerow([r.get(k, "") for k, _ in CSV_COLUMNS])
    return buf.getvalue()

def generate_weekly_reports():
    leagues = run_query(f"""
        SELECT DISTINCT l.league_id, l.league_name
        FROM club_season cs JOIN league l ON cs.league_id = l.league_id
        WHERE cs.season_id = {LATEST_SEASON}
    """)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")          # CHANGED: added time so runs don't overwrite
    for lg in leagues:
        rows = build_league_summary(lg["league_id"])
        if not rows:
            continue
        safe = lg["league_name"].replace(" ", "_").replace("/", "-")
        with open(os.path.join(REPORTS_DIR, f"league_summary_{safe}_{stamp}.csv"),
                  "w", newline="", encoding="utf-8-sig") as f:   # CHANGED: utf-8-sig so Excel shows accents
            f.write(rows_to_csv(rows))

# CHANGED: schedule settings, edit these to change when it runs
SCHEDULE_DAY = "wed"     # mon, tue, wed, thu, fri, sat, sun, or "*" for every day
SCHEDULE_HOUR = 16      # 24-hour clock
SCHEDULE_MINUTE = 49

scheduler = BackgroundScheduler()
scheduler.add_job(generate_weekly_reports, "cron",
                  day_of_week=SCHEDULE_DAY, hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE,
                  id="weekly_league_summary", replace_existing=True,
                  coalesce=True, misfire_grace_time=3600)
scheduler.start()
print("[scheduler] Weekly league summary next run:",
      scheduler.get_job("weekly_league_summary").next_run_time)

@app.get("/reports/league-summary/files")
def list_report_files():
    files = []
    names = [n for n in os.listdir(REPORTS_DIR) if n.endswith(".csv")]
    # CHANGED: newest first instead of alphabetical
    names.sort(key=lambda n: os.path.getmtime(os.path.join(REPORTS_DIR, n)), reverse=True)
    for name in names:
        full = os.path.join(REPORTS_DIR, name)
        files.append({"name": name,
                      "generated_at": datetime.fromtimestamp(os.path.getmtime(full)).isoformat()})
    return files

@app.get("/reports/league-summary/files/{name}")
def download_report_file(name: str):
    safe = os.path.basename(name)                 # blocks ../ path traversal
    path = os.path.join(REPORTS_DIR, safe)
    if not os.path.exists(path):
        raise HTTPException(404, "Report not found")
    return FileResponse(path, media_type="text/csv", filename=safe)

@app.post("/reports/league-summary/generate")
def generate_now():
    generate_weekly_reports()
    return {"ok": True}