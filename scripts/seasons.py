# Fills the season table with data from the SEASON_ID, SEASON_NAME, and SEASON_START_YEAR lists

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
 
SEASON_ID = [1718, 1819, 1920, 2021, 2122, 2223, 2324, 2425, 2526, 2627]
SEASON_NAME = ["2017/18", "2018/19", "2019/20", "2020/21", "2021/22", "2022/23", "2023/24", "2024/25", "2025/26", "2026/27"]
SEASON_START_YEAR = [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]

def insert_seasons():
    count = 0
 
    for row in SEASON_ID:
        season_id = SEASON_ID[count]
        season_name = SEASON_NAME[count]
        start_year = SEASON_START_YEAR[count]

        cursor.execute("""
            INSERT INTO season (season_id, season_name, start_year)
            VALUES (%s, %s, %s) AS new
                ON DUPLICATE KEY UPDATE
                    season_id = new.season_id,
                    season_name = new.season_name,
                    start_year = new.start_year
            """, (season_id, season_name, start_year))  # safe to re-run
        count += 1
 
    conn.commit()
    print(f"{count} seasons inserted/updated")
 
 
insert_seasons()
 
cursor.close()
conn.close()
print("Done!")