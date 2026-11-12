import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal
 
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
 
from database import get_connection, get_readonly_connection
 
router = APIRouter()
 
ROW_LIMIT = 500                  # max rows sent back to the page
MAX_EXECUTION_MS = 10_000        # MySQL kills SELECTs that run longer than this
ALLOWED_STATEMENTS = {"select", "show", "describe", "desc", "explain"}
 
 
class LoginBody(BaseModel):
    username: str
    password: str
 
 
class QueryBody(BaseModel):
    sql: str
 
 
def as_tuple(row):
    """Works whether database.py returns tuple rows or dict rows."""
    return tuple(row.values()) if isinstance(row, dict) else tuple(row)
 
 
def json_safe(value):
    """Convert MySQL types the JSON encoder can't handle."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, timedelta):
        return str(value)
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    return str(value)
 
 
# auth 
 
def require_login(request: Request):
    """Runs before every protected endpoint. No session -> 401."""
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Not logged in")
    return {"user_id": request.session["user_id"], "username": request.session["username"]}
 
 
@router.post("/auth/login")
def login(body: LoginBody, request: Request):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT UserID, Username, PasswordHash FROM Users WHERE Username = %s",
            (body.username.strip(),),
        )
        row = cur.fetchone()
    finally:
        conn.close()
 
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    user_id, username, password_hash = as_tuple(row)
    if not bcrypt.checkpw(body.password.encode(), password_hash.encode()):
        raise HTTPException(status_code=401, detail="Invalid username or password")
 
    request.session.clear()
    request.session["user_id"] = user_id
    request.session["username"] = username
    return {"username": username}
 
 
@router.get("/auth/me")
def me(user=Depends(require_login)):
    return {"username": user["username"]}
 
 
@router.post("/auth/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}
 
 
# query console 
 
@router.post("/admin/query")
def run_query(body: QueryBody, user=Depends(require_login)):
    # require_login has already checked the session for this exact request
    sql = body.sql.strip().rstrip(";").strip()
    if not sql:
        raise HTTPException(status_code=400, detail="Query is empty.")
    if ";" in sql:  # also blocks ';' inside string literals; fine for a console
        raise HTTPException(status_code=400, detail="Only one statement can be run at a time.")
    first_word = sql.split(None, 1)[0].lower()
    if first_word not in ALLOWED_STATEMENTS:
        raise HTTPException(
            status_code=400,
            detail="Only read-only queries are allowed (SELECT, SHOW, DESCRIBE, EXPLAIN).",
        )
    if re.search(r"\binto\s+(outfile|dumpfile)\b", sql, re.IGNORECASE):
        raise HTTPException(status_code=400, detail="Writing to files is not allowed.")

        # SELECT-only database user: the database itself refuses writes,
    # even if a check above misses something
    try:
        conn = get_readonly_connection()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not connect to the database: {e}")

    try:
        cur = conn.cursor()
        cur.execute(f"SET SESSION MAX_EXECUTION_TIME = {MAX_EXECUTION_MS}")
        cur.execute(sql)

        columns = [d[0] for d in cur.description] if cur.description else []
        # only pull ROW_LIMIT + 1 rows into memory, so SELECT * on a big
        # table can't run the free-tier server out of RAM
        rows = cur.fetchmany(ROW_LIMIT + 1) if columns else []
    except Exception as e:  # SQL errors (bad syntax, unknown table, no permission...) go back to the page
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        try:
            conn.close()
        except Exception:
            pass  # closing with unread rows left over can complain; safe to ignore

    return {
        "columns": columns,
        "rows": [[json_safe(v) for v in as_tuple(r)] for r in rows[:ROW_LIMIT]],
        "row_count": min(len(rows), ROW_LIMIT),
        "truncated": len(rows) > ROW_LIMIT,
    }