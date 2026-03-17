"""Database connection module."""
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
from dotenv import load_dotenv
import os
from urllib.parse import quote_plus, urlparse

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR.parent / ".env")
def _build_mongo_url(db_name: str) -> str:
    mongo_url = os.environ.get("MONGO_URL") or os.environ.get("MONGO_URI")
    if mongo_url:
        return mongo_url

    host = os.environ.get("MONGO_HOST", "localhost")
    port = os.environ.get("MONGO_PORT", "27017")
    username = os.environ.get("MONGO_ROOT_USERNAME") or os.environ.get("MONGO_USERNAME")
    password = os.environ.get("MONGO_ROOT_PASSWORD") or os.environ.get("MONGO_PASSWORD")

    if username and password:
        auth_db = os.environ.get("MONGO_AUTH_DB", "admin")
        return (
            f"mongodb://{quote_plus(username)}:{quote_plus(password)}"
            f"@{host}:{port}/{db_name}?authSource={quote_plus(auth_db)}"
        )

    return f"mongodb://{host}:{port}/{db_name}"


db_name = os.environ.get("DB_NAME", "saas_db")
mongo_url = _build_mongo_url(db_name)

if not os.environ.get("DB_NAME"):
    parsed = urlparse(mongo_url)
    db_name = parsed.path.lstrip("/") or "saas_db"

client = AsyncIOMotorClient(mongo_url)
db = client[db_name]


async def close_db():
    client.close()
