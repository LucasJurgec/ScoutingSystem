import os
from dotenv import load_dotenv
from mysql.connector import pooling
from pymongo import MongoClient

load_dotenv()  # reads backend/.env


# ---------- MySQL (structured + contract JSON) ----------

def _mysql_config():
    config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 3306)),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME"),
    }
    # Only turn on SSL when a cert is set (cloud host later).
    # Local MySQL in DBeaver doesn't need it.
    ssl_ca = os.getenv("DB_SSL_CA")
    if ssl_ca:
        config["ssl_ca"] = ssl_ca
        config["ssl_verify_cert"] = True
    return config


# A small pool so every request isn't opening a brand new connection.
_pool = pooling.MySQLConnectionPool(
    pool_name="scouting_pool",
    pool_size=5,
    **_mysql_config(),
)


def get_connection():
    # conn.close() hands it back to the pool, so your old
    # cursor.close(); conn.close() pattern still works as-is.
    return _pool.get_connection()


# ---------- MongoDB Atlas (scouting reports) ----------

_mongo_client = MongoClient(os.getenv("MONGODB_URI"))


def get_reports_collection():
    db = _mongo_client[os.getenv("MONGO_DB", "scouting_system")]
    return db[os.getenv("MONGO_COLLECTION", "scouting_reports")]
