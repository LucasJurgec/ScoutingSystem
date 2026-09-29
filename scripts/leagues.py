# Fills the league table with data from competitions.csv
# CSV file won't run as it has been moved to a different location

import csv
import os
import mysql.connector
from dotenv import load_dotenv
 
load_dotenv()
 
COMPETITIONS_CSV = "datasets/competitions.csv"
 
conn = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT")),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
)
cursor = conn.cursor()
 
# Transfermarkt country name -> name used in your nation table, for any that differ
COUNTRY_ALIASES = {
    "Türkiye": "Turkey",
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Czechia": "Czech Republic",
    "Ireland": "Republic of Ireland",
}
 
def tidy_name(raw_name):
    return raw_name.replace("-", " ").title()  # "super-league-1" -> "Super League 1"
 
 
def insert_leagues():
    # nation name -> nation_code
    cursor.execute("SELECT nation_name, nation_code FROM nation")
    name_to_code = {name: code for name, code in cursor.fetchall()}
 
    inserted, already_there, no_match = 0, 0, []
 
    with open(COMPETITIONS_CSV, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["type"] != "domestic_league":  # skip cups, UCL, etc.
                continue
 
            country = COUNTRY_ALIASES.get(row["country_name"], row["country_name"])
            nation_code = name_to_code.get(country)
            if nation_code is None:
                no_match.append(f'{row["name"]} ({row["country_name"]})')
                continue
 
            league_name = tidy_name(row["name"])
 
            # stops duplicates if you re-run it (two "Bundesliga"s exist, so check name + nation together)
            cursor.execute(
                "SELECT 1 FROM league WHERE league_name = %s AND nation_code = %s",
                (league_name, nation_code),
            )
            if cursor.fetchone():
                already_there += 1
                continue
 
            cursor.execute(
                "INSERT INTO league (league_name, nation_code) VALUES (%s, %s)",
                (league_name, nation_code),
            )
            inserted += 1
 
    conn.commit()
    print(f"{inserted} leagues inserted, {already_there} already in the table")
    if no_match:
        print("NO NATION MATCH (add to COUNTRY_ALIASES):", ", ".join(no_match))
 
 
insert_leagues()
 
cursor.close()
conn.close()
print("Done!")