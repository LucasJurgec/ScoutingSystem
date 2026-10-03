"""
Validate every contract clause JSON file, then write the valid ones into the
existing contract_information.contract_data column.

Checks run before anything is written:
  1. Syntax   - is it valid JSON?
  2. Schema   - right keys and types? (contract_clauses.schema.json)
  3. Business - the player must already have a row in contract_information
                (we UPDATE existing rows, we don't create them), the filename
                must match player_id, and any club a clause refers to must
                exist in the club table.

If ANY file fails, nothing is loaded.

Run from the repo root:  python scripts/load_contract_data.py
"""
import json
import os
import sys
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from jsonschema import Draft202012Validator, FormatChecker

DATA_DIR = Path("datasets/json")
SCHEMA_PATH = Path("schemas/contract_clauses.schema.json")


def connect():
    load_dotenv()
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )


def load_reference_data(conn):
    cur = conn.cursor()
    cur.execute("SELECT player_id FROM contract_information")
    contract_player_ids = {row[0] for row in cur.fetchall()}
    cur.execute("SELECT club_id FROM club")
    club_ids = {row[0] for row in cur.fetchall()}
    cur.close()
    return contract_player_ids, club_ids


def business_checks(doc, contract_player_ids, club_ids):
    problems = []
    if doc["player_id"] not in contract_player_ids:
        problems.append(
            f"player_id {doc['player_id']} has no row in contract_information"
        )
    for i, clause in enumerate(doc["clauses"]):
        for key in ("from_club_id", "club_id"):
            if key in clause and clause[key] not in club_ids:
                problems.append(f"clauses/{i}: {key} {clause[key]} does not exist in club")
    return problems


def validate_all(conn):
    schema = json.loads(SCHEMA_PATH.read_text())
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    contract_player_ids, club_ids = load_reference_data(conn)

    valid_docs, errors = [], []

    for path in sorted(DATA_DIR.glob("*.json")):
        try:
            doc = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            errors.append(f"[SYNTAX]   {path.name}: {e}")
            continue

        schema_errs = list(validator.iter_errors(doc))
        if schema_errs:
            for err in schema_errs:
                loc = "/".join(map(str, err.absolute_path)) or "(root)"
                errors.append(f"[SCHEMA]   {path.name} -> {loc}: {err.message}")
            continue

        if path.stem != str(doc["player_id"]):
            errors.append(f"[NAMING]   {path.name}: filename should be {doc['player_id']}.json")
            continue

        biz = business_checks(doc, contract_player_ids, club_ids)
        if biz:
            errors.extend(f"[BUSINESS] {path.name}: {p}" for p in biz)
            continue

        valid_docs.append(doc)

    return valid_docs, errors


def load(conn, docs):
    cur = conn.cursor()
    updated = 0
    for doc in docs:
        cur.execute(
            "UPDATE contract_information SET contract_data = %s WHERE player_id = %s",
            (json.dumps(doc), doc["player_id"]),
        )
        updated += cur.rowcount
    conn.commit()
    cur.close()
    return updated


def main():
    conn = connect()
    docs, errors = validate_all(conn)

    if errors:
        print("\n".join(errors))
        print(f"\n{len(errors)} problem(s) found. Nothing loaded.")
        conn.close()
        sys.exit(1)

    updated = load(conn, docs)
    conn.close()
    print(f"Validated {len(docs)} files, updated {updated} rows in contract_information.")


if __name__ == "__main__":
    main()
