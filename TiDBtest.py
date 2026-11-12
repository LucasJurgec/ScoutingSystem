import time
from database import get_connection

conn = get_connection()
cur = conn.cursor()

t = time.perf_counter()
cur.execute("SELECT 1")
cur.fetchall()
print(f"round trip: {(time.perf_counter()-t)*1000:.0f} ms")

t = time.perf_counter()
cur.execute("SELECT COUNT(*) FROM player_stats")
cur.fetchall()
print(f"count query: {(time.perf_counter()-t)*1000:.0f} ms")