# Fills the position table with data from the POSITIONS list

import os
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
 
POSITIONS = [
    ("Goalkeeper", "GK"),
    ("Defender", "RB"),
    ("Defender", "LB"),
    ("Defender", "CB"),

    ("Midfielder", "DM"),
    ("Midfielder", "CM"),
    ("Midfielder", "AM"),
    ("Midfielder", "RM"),
    ("Midfielder", "LM"),

    ("Attacker", "RW"),
    ("Attacker", "LW"),
    ("Attacker", "ST")
]

def insert_seasons():
 
    for position_general, position_advanced in POSITIONS:

        print(repr(position_general), repr(position_advanced))

        cursor.execute("""
            INSERT INTO position (position_general, position_advanced)
            VALUES (%s, %s) AS new
                ON DUPLICATE KEY UPDATE
                    position_general = new.position_general,
                    position_advanced = new.position_advanced
            """, (position_general, position_advanced))  # safe to re-run
 
    conn.commit()
 
insert_seasons()
 
cursor.close()
conn.close()
print("Done!")