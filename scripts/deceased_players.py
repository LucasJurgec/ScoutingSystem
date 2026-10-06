"""
Transfermarkt shows deceased players' photos in black and white.
This checks every 'Free Agent' player's photo and prints the ones with
almost no colour, so you can review them by hand. It doesn't change anything.
 
Needs: pip install pillow requests
Run from the folder that has database.py and .env.
"""
import io
import requests
from PIL import Image, ImageStat
from database import get_connection
 
SATURATION_THRESHOLD = 15  # 0-255; true black-and-white photos sit near 0
 
conn = get_connection()
cur = conn.cursor(dictionary=True)
cur.execute("""
    SELECT player_id, first_name, last_name, player_img
    FROM player
    WHERE status = 'Free Agent' AND player_img IS NOT NULL
""")
players = cur.fetchall()
cur.close()
conn.close()
 
print(f"Checking {len(players)} free agents...\n")
 
 
def mean_saturation(url):
    resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content)).convert("HSV")
    return ImageStat.Stat(img).mean[1]
 
 
for p in players:
    # the Transfermarkt placeholder silhouette is grey too, so skip it
    if "default" in p["player_img"]:
        continue
    try:
        sat = mean_saturation(p["player_img"])
    except Exception as e:
        print(f"  skipped {p['player_id']} ({e})")
        continue
    if sat < SATURATION_THRESHOLD:
        name = " ".join(filter(None, [p["first_name"], p["last_name"]]))
        print(f"{p['player_id']}\t{name}\tsaturation={sat:.1f}")