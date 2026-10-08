import os
import json
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from database import get_connection, get_reports_collection
 
app = FastAPI(title="Scouting System API")
 
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
 
 
# ---------- helper ----------
 
def run_query(sql, params=(), one=False):
    """Runs a SELECT and returns rows as dicts (or one dict / None)."""
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
 
 
# ---------- basic ----------
 
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
 
 
# ---------- players ----------
 
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
 
 
# ---------- chatbot ----------
 
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
    try:
        return ask(req.message, req.history)
    except RuntimeError as e:                      # e.g. GOOGLE_API_KEY missing
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        text = str(e)
        import traceback; traceback.print_exc()
        if "429" in text or "RESOURCE_EXHAUSTED" in text or "quota" in text.lower():
            raise HTTPException(status_code=429, detail="The AI model's free-tier limit was hit. Wait a minute and try again.")
        if "Recursion limit" in text:
            raise HTTPException(status_code=500, detail="The assistant couldn't work that one out. Try rephrasing the question.")
        raise HTTPException(status_code=500, detail="Something went wrong answering that question.")
 
 
# ---------- filter dropdowns ----------
 
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
