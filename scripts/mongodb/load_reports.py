"""
Embed the generated scouting reports and load every player's document into
MongoDB Atlas.
 
What it does:
  1. Reads data/reports/reports.json (from generate_reports.py).
  2. For each GENERATED report, turns report_text into an embedding (a vector)
     using a small model that runs locally - free, no API key.
  3. Upserts ALL documents into the `report` collection, matched on player_id so
     re-running overwrites cleanly (same idea as ON DUPLICATE KEY UPDATE in MySQL).
     Placeholders go in with an empty report_text and embedding = None.
 
The document stored per player:
  { player_id, report_text, embedding, last_updated, source }
 
Run from the repo root:  python scripts/load_reports.py
 
Needs MONGO_URI in your .env.
"""
import os
import json
 
from pymongo import MongoClient, UpdateOne
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
 
INPUT = "data/reports/reports.json"
DB_NAME = "scoutingReports"      # the database shown in Atlas
COLL_NAME = "report"             # the collection shown in Atlas
MODEL_NAME = "all-MiniLM-L6-v2"  # 384-dim embeddings - remember 384 for the index step
WRITE_BATCH = 200
 
 
def main():
    load_dotenv()                          # reads .env if present
    load_dotenv("atlas-credentials.env")   # fallback: fills MONGO_URI if it lives here
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise SystemExit(
            "MONGO_URI not found. Add it to your .env (or atlas-credentials.env). "
            "Without it, pymongo defaults to localhost and the connection fails."
        )
 
    with open(INPUT, encoding="utf-8") as f:
        docs = json.load(f)
 
    # 1. embed only the generated reports (placeholders have no text)
    to_embed = [d for d in docs if d["source"] == "generated" and d["report_text"].strip()]
    print(f"Embedding {len(to_embed)} generated reports (first run downloads the model, ~90MB)...")
 
    model = SentenceTransformer(MODEL_NAME)
    vectors = model.encode(
        [d["report_text"] for d in to_embed],
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    for d, v in zip(to_embed, vectors):
        d["_embedding"] = v.tolist()
 
    # 2. upsert everything into Atlas
    client = MongoClient(uri, serverSelectionTimeoutMS=20000)
    coll = client[DB_NAME][COLL_NAME]
 
    ops, done = [], 0
    for d in docs:
        doc = {
            "player_id": d["player_id"],
            "report_text": d["report_text"],
            "embedding": d.get("_embedding"),   # None for placeholders
            "last_updated": d["last_updated"],
            "source": d["source"],
        }
        ops.append(UpdateOne({"player_id": d["player_id"]}, {"$set": doc}, upsert=True))
        if len(ops) >= WRITE_BATCH:
            coll.bulk_write(ops)
            done += len(ops)
            print(f"  upserted {done}/{len(docs)}")
            ops = []
    if ops:
        coll.bulk_write(ops)
        done += len(ops)
 
    with_vec = coll.count_documents({"embedding": {"$ne": None}})
    total = coll.count_documents({})
    client.close()
 
    print(f"\nDone. {total} documents in '{DB_NAME}.{COLL_NAME}', {with_vec} with an embedding.")
    print("Next: create the vector search index in Atlas (dimensions = 384, similarity = cosine).")
 
 
if __name__ == "__main__":
    main()