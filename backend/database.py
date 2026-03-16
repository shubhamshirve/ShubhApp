"""Database connection module."""
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
from dotenv import load_dotenv
import os
from urllib.parse import urlparse

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR.parent / ".env")

mongo_url = (
    os.environ.get("MONGO_URL")
    or os.environ.get("MONGO_URI")
    or "mongodb://localhost:27017/saas_db"
)

db_name = os.environ.get("DB_NAME")
if not db_name:
    parsed = urlparse(mongo_url)
    db_name = parsed.path.lstrip("/") or "saas_db"

client = AsyncIOMotorClient(mongo_url)
db = client[db_name]


async def close_db():
    client.close()
