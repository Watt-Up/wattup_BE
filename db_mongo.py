from pymongo import MongoClient
from config import settings

client = MongoClient(settings.MONGO_URL)
mongo_db = client[settings.MONGO_DB]

def get_mongo():
    return mongo_db