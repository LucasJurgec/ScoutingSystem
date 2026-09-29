# Fills the club table with data from clubs_v2.csv
# CSV file won't run as it has been moved to a different location

import csv
import os
import mysql.connector
from dotenv import load_dotenv
 
load_dotenv()
 
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ScoutingSystem folder
CLUBS_CSV = "datasets/clubs_v2.csv"
 
# Transfermarkt crest URL, {} gets replaced with the club_id
LOGO_URL = "https://tmssl.akamaized.net//images/wappen/head/{}.png"
 
conn = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT")),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
)
cursor = conn.cursor()
 
 
def insert_clubs():
    count = 0
 
    with open(CLUBS_CSV, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            club_id = int(row["club_id"])
            club_name = row["name"].strip()
            club_logo = LOGO_URL.format(club_id)
 
            cursor.execute("""
                INSERT INTO club (club_id, club_name, club_logo)
                VALUES (%s, %s, %s) AS new
                ON DUPLICATE KEY UPDATE
                    club_name = new.club_name,
                    club_logo = new.club_logo
            """, (club_id, club_name, club_logo))  # safe to re-run
            count += 1
 
    conn.commit()
    print(f"{count} clubs inserted/updated")
 
 
insert_clubs()
 
cursor.close()
conn.close()
print("Done!")