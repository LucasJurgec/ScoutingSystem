"""
Scouting chatbot.
 
A LangChain agent (Gemini) with two tools:
  - run_sql                  -> read-only SELECT queries on MySQL (structured data)
  - search_scouting_reports  -> semantic search over the MongoDB reports (unstructured data)
 
The LLM decides which tool(s) to call for each question, then writes the answer
from what the tools returned.
"""
import os
import re
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import pooling
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from database import get_reports_collection
 
load_dotenv()
 
MAX_ROWS = 25          # most rows a single SQL query can hand back to the LLM
MAX_TOOL_CHARS = 6000  # keeps tool output (and token usage) small
HISTORY_TURNS = 6      # previous messages sent along for follow-up questions
 
 
# ---------- read-only MySQL connection ----------
# Separate pool using the chatbot_ro user, which MySQL only allows to SELECT.
# Even if the model wrote a DELETE or DROP, the database would refuse it.
 
_ro_pool = None
 
def get_readonly_connection():
    global _ro_pool
    if _ro_pool is None:
        config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", 3306)),
            "user": os.getenv("CHATBOT_DB_USER"),
            "password": os.getenv("CHATBOT_DB_PASSWORD"),
            "database": os.getenv("DB_NAME"),
        }
        if os.getenv("DB_SSL_CA"):
            config["ssl_ca"] = os.getenv("DB_SSL_CA")
            config["ssl_verify_cert"] = True
        _ro_pool = pooling.MySQLConnectionPool(pool_name="chatbot_ro_pool", pool_size=3, **config)
    return _ro_pool.get_connection()
 
 
def run_select(sql, params=()):
    conn = get_readonly_connection()
    try:
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute(sql, params)
        rows = cursor.fetchmany(MAX_ROWS)
        cursor.close()
        return rows
    finally:
        conn.close()
 
 
def to_text(rows):
    """Compact plain-text table for the LLM: header line, then one line per row."""
    if not rows:
        return "No rows returned."
    cols = list(rows[0].keys())
    lines = [" | ".join(cols)]
    for r in rows:
        lines.append(" | ".join("NULL" if r[c] is None else str(r[c]) for c in cols))
    return "\n".join(lines)[:MAX_TOOL_CHARS]
 
 
# ---------- tool 1: SQL ----------
 
@tool
def run_sql(query: str) -> str:
    """Run ONE read-only MySQL SELECT query against the scouting database and
    return the rows. Use for anything factual or numeric: stats, ages, positions,
    clubs, leagues, nations, market values, contracts, transfers. Always include
    player_id and a name column when returning players. Use LIMIT 25 or less."""
    cleaned = query.strip().rstrip(";")
    if ";" in cleaned:
        return "Error: only one statement is allowed."
    if not re.match(r"^\s*(SELECT|WITH)\b", cleaned, re.IGNORECASE):
        return "Error: only SELECT queries are allowed."
    try:
        return to_text(run_select(cleaned))
    except mysql.connector.Error as e:
        # hand the error back so the model can fix its query
        return f"SQL error: {e.msg}"
 
 
# ---------- tool 2: semantic search over scouting reports ----------
 
_embedder = None
 
def get_embedder():
    # Must be the SAME model that created the stored embeddings (384 dimensions).
    # Loaded on first use; the first ever run downloads it (~90 MB).
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _embedder
 
 
@tool
def search_scouting_reports(query: str, player_ids: str = "", limit: int = 5) -> str:
    """Semantic search over the written scouting reports. Use for questions about
    playing style, qualities, strengths, weaknesses or how a player is described
    (e.g. "good in the air", "creative passer", "struggles defensively"). Matches
    meaning, not exact words.
    query: describe the quality you're looking for in plain English.
    player_ids: optional comma-separated player_ids (e.g. from run_sql) to only
    search those players' reports.
    limit: number of reports to return (1-10)."""
    limit = max(1, min(int(limit), 10))
    vector = get_embedder().encode(query).tolist()
 
    stage = {
        "index": "report_vector_index",
        "path": "embedding",
        "queryVector": vector,
        "numCandidates": max(100, limit * 20),
        "limit": limit,
    }
    ids = [int(x) for x in re.findall(r"\d+", player_ids or "")]
    if ids:
        stage["filter"] = {"player_id": {"$in": ids}}
 
    try:
        docs = list(get_reports_collection().aggregate([
            {"$vectorSearch": stage},
            {"$project": {"_id": 0, "player_id": 1, "report_text": 1,
                          "score": {"$meta": "vectorSearchScore"}}},
        ]))
    except Exception as e:
        return f"Report search is unavailable: {e}"
    if not docs:
        return "No matching reports."
 
    # attach names from MySQL so the answer can mention players properly
    found = [d["player_id"] for d in docs]
    placeholders = ", ".join(["%s"] * len(found))
    names = {
        r["player_id"]: r["name"]
        for r in run_select(
            f"SELECT player_id, CONCAT_WS(' ', first_name, last_name) AS name "
            f"FROM player WHERE player_id IN ({placeholders})", tuple(found))
    }
 
    out = []
    for d in docs:
        text = re.sub(r"\s+", " ", d.get("report_text", "")).strip()
        out.append(f"player_id={d['player_id']} | name={names.get(d['player_id'], 'unknown')} | "
                   f"match={d['score']:.2f}\n{text}")
    return "\n\n".join(out)[:MAX_TOOL_CHARS]
 
 
# ---------- the agent ----------
 
SYSTEM_PROMPT = """You are a football scouting assistant for a club's recruitment staff.
You answer questions using two tools and nothing else: run_sql (MySQL 8, structured data)
and search_scouting_reports (semantic search over written scouting reports).
 
WHICH TOOL
- Numbers and facts (stats, age, position, club, league, value, contract) -> run_sql.
- Playing style, qualities, strengths, weaknesses, "players like..." -> search_scouting_reports.
- Both (e.g. "U23 midfielders who are good passers"): run_sql first to get matching
  player_ids (LIMIT 50), then search_scouting_reports with those ids in player_ids.
 
DATABASE (MySQL 8) - only these tables exist
player(player_id, first_name NULLABLE, last_name, date_of_birth, height [cm], position_id,
       club_id NULLABLE [current club; NULL for free agents/retired], nation_code,
       status ENUM('Active','Free Agent','Retired','Deceased'))
position(position_id, position_general ENUM('Goalkeeper','Defender','Midfielder','Attacker'),
         position_advanced ENUM('GK','RB','LB','CB','DM','CM','AM','LM','RM','LW','RW','ST'))
  player.position_id = PRIMARY position. player_position(player_id, position_id) = SECONDARY positions.
club(club_id, club_name, club_logo)
club_season(club_id, season_id, league_id)  -- league a club played in each season
league(league_id, league_name, nation_code)
nation(nation_code CHAR(3) e.g. 'ENG','ESP', nation_name)
season(season_id, season_name e.g. '2024-25', start_year)  -- higher season_id = more recent
player_stats(stat_id, player_id, club_id, season_id, appearances, minutes_played, goals, assists,
             penalty_scored, penalty_attempts, yellow_cards, red_cards, own_goals, shots_total,
             shots_on_target, crosses, fouls_committed, fouls_drawn, offsides, tackles_won,
             interceptions, points_per_match, plus_minus, xg, xa, key_passes)
goalkeeper_stats(stat_id -> player_stats.stat_id, goals_conceded, shots_on_target_against, saves,
                 clean_sheets, penalties_faced, penalty_conceded, penalty_saved, penalty_missed)
market_value(player_id, market_value [EUR], value_date)  -- full history, one row per valuation
contract_information(player_id, contract_start, contract_expiry, weekly_wage [EUR],
                     release_clause [EUR], contract_data JSON)  -- only some players have a row
transfer(player_id, from_club_id, to_club_id, transfer_type ENUM('Free','Permanent','Loan'),
         transfer_date, transfer_fee [EUR], loan_end_date)
shortlist(player_id, date_added)
 
RULES FOR SQL
- player_stats has ONE ROW PER PLAYER PER SEASON PER CLUB. For season totals use SUM() with
  GROUP BY player_id, because a player who moved mid-season has two rows.
- Latest season: season_id = (SELECT MAX(season_id) FROM player_stats). Use it when no season is given.
- Current market value = the row with the latest value_date for that player (see example).
- Current league of a club = club_season row with the highest season_id for that club.
- Age: TIMESTAMPDIFF(YEAR, date_of_birth, CURDATE()).
- Name: CONCAT_WS(' ', first_name, last_name). Search names with LIKE '%...%'.
- Many stat columns are NULL where data wasn't available; NULL means unknown, not zero.
- When asked for players to sign or scout, only include status = 'Active' unless told otherwise.
- Select only the columns you need. Never more than LIMIT 25.
 
EXAMPLES
-- Top scorers this season
SELECT p.player_id, CONCAT_WS(' ', p.first_name, p.last_name) AS name, SUM(ps.goals) AS goals
FROM player_stats ps JOIN player p ON p.player_id = ps.player_id
WHERE ps.season_id = (SELECT MAX(season_id) FROM player_stats)
GROUP BY p.player_id, name ORDER BY goals DESC LIMIT 10;
 
-- Most valuable active players under 21
SELECT p.player_id, CONCAT_WS(' ', p.first_name, p.last_name) AS name,
       TIMESTAMPDIFF(YEAR, p.date_of_birth, CURDATE()) AS age, mv.market_value
FROM player p JOIN market_value mv ON mv.player_id = p.player_id
WHERE mv.value_date = (SELECT MAX(value_date) FROM market_value WHERE player_id = p.player_id)
  AND p.status = 'Active' AND TIMESTAMPDIFF(YEAR, p.date_of_birth, CURDATE()) < 21
ORDER BY mv.market_value DESC LIMIT 10;
 
-- Defensive midfielders in the Premier League (current league via club_season)
SELECT p.player_id, CONCAT_WS(' ', p.first_name, p.last_name) AS name, c.club_name
FROM player p
JOIN position pos ON pos.position_id = p.position_id
JOIN club c ON c.club_id = p.club_id
JOIN club_season cs ON cs.club_id = c.club_id
     AND cs.season_id = (SELECT MAX(season_id) FROM club_season WHERE club_id = c.club_id)
JOIN league l ON l.league_id = cs.league_id
WHERE pos.position_advanced = 'DM' AND l.league_name LIKE '%Premier League%' AND p.status = 'Active'
LIMIT 25;
 
-- Contracts expiring in the next 12 months
SELECT p.player_id, CONCAT_WS(' ', p.first_name, p.last_name) AS name, ci.contract_expiry
FROM contract_information ci JOIN player p ON p.player_id = ci.player_id
WHERE ci.contract_expiry BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 12 MONTH)
ORDER BY ci.contract_expiry LIMIT 25;
 
ANSWERING
- Be concise and specific. Name players and quote the numbers the tools returned.
- Never invent stats, players or report content. If the tools returned nothing useful, say so.
- Money is in euros. Write large values like EUR 45m or EUR 850k.
- Don't show SQL or tool names in your answer unless the user asks."""
 
_agent = None
 
def get_agent():
    global _agent
    if _agent is None:
        if not os.getenv("GOOGLE_API_KEY"):
            raise RuntimeError("GOOGLE_API_KEY is not set in .env")
        # Gemini 3.x models are tuned to run at their default temperature (1.0);
        # forcing 0 can make them loop or degrade, so we leave it alone.
        model = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            max_retries=1,     # don't burn free-tier quota retrying
        )
        _agent = create_agent(model, tools=[run_sql, search_scouting_reports], system_prompt=SYSTEM_PROMPT)
    return _agent
 
 
def ask(message, history=None):
    """Run one chat turn. history = [{"role": "user"|"assistant", "content": "..."}]
    Returns the answer plus the tool calls made, so the UI can show the SQL used."""
    messages = [
        {"role": m["role"], "content": m["content"]}
        for m in (history or [])[-HISTORY_TURNS:]
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]
    messages.append({"role": "user", "content": message})
 
    # recursion_limit caps the think -> tool -> think loop so a confused
    # model can't burn through the free-tier quota on one question
    result = get_agent().invoke({"messages": messages}, config={"recursion_limit": 10})
 
    steps = []
    for m in result["messages"]:
        for call in getattr(m, "tool_calls", None) or []:
            steps.append({"tool": call["name"], "input": call["args"]})
 
    return {"answer": result["messages"][-1].text, "steps": steps}