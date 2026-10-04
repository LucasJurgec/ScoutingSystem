
"""
Test the vector search: type a description, get the closest-matching players.
 
How it works:
  1. Your phrase is embedded with the SAME model used to build the stored vectors.
  2. MongoDB's $vectorSearch compares it against every report's `embedding`
     and returns the nearest matches by meaning (not keywords).
  3. We print the player_id, score, and report so you can eyeball the match.
 
To link results back to full player info, use the player_id against MySQL.
 
Run from the repo root:  python scripts/search_reports.py
"""
import os
 
from pymongo import MongoClient
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
 
DB_NAME = "scoutingReports"
COLL_NAME = "report"
INDEX_NAME = "vector_index"       # must match the index name you created in Atlas
MODEL_NAME = "all-MiniLM-L6-v2"   # same model as load_reports.py
NUM_RESULTS = 5
 
 
def search(coll, model, query):
    qvec = model.encode(query, normalize_embeddings=True).tolist()
    pipeline = [
        {
            "$vectorSearch": {
                "index": INDEX_NAME,
                "path": "embedding",
                "queryVector": qvec,
                "numCandidates": 100,   # how many to scan (bigger = more accurate, slower)
                "limit": NUM_RESULTS,   # how many to return
            }
        },
        {
            "$project": {
                "_id": 0,
                "player_id": 1,
                "report_text": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]
    return list(coll.aggregate(pipeline))
 
 
def main():
    load_dotenv()
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise SystemExit("MONGODB_URI not found in .env / atlas-credentials.env")
 
    print("Loading model...")
    model = SentenceTransformer(MODEL_NAME)
    client = MongoClient(uri, serverSelectionTimeoutMS=20000)
    coll = client[DB_NAME][COLL_NAME]
 
    print("Type a description of the player you want (or 'quit').\n"
          "e.g. 'clinical finisher', 'creative playmaker with discipline issues',\n"
          "     'ball-winning defensive midfielder'\n")
 
    while True:
        query = input("search> ").strip()
        if query.lower() in {"quit", "exit", ""}:
            break
        results = search(coll, model, query)
        if not results:
            print("  no matches - is the index 'Ready' and named correctly?\n")
            continue
        for r in results:
            score = round(r.get("score", 0), 3)
            first_line = r["report_text"].split("\n")[0]
            print(f"\n  [{r['player_id']}] score={score}  {first_line}")
            for line in r["report_text"].split("\n")[1:]:
                if line.strip():
                    print(f"      {line}")
        print()
 
    client.close()
 
 
if __name__ == "__main__":
    main()