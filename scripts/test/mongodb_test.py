import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.getenv("MONGODB_URI"))
print(client.admin.command("ping"))
print("Databases:", client.list_database_names())