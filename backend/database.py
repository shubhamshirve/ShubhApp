"""Database connection module."""
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
from dotenv import load_dotenv
import os
from urllib.parse import quote_plus, urlparse

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR.parent / ".env")

def _build_mongo_url(db_name: str) -> str:
    """
    Build MongoDB URL from environment variables.
    
    Priority:
    1. MONGO_URI (use this in Docker environments)
    2. Build from individual components (MONGO_HOST, MONGO_PORT, etc.)
    
    MONGO_URI should be: mongodb://[user:pass@]host:port/database?authSource=admin
    """
    mongo_uri = os.environ.get("MONGO_URI")
    
    # If MONGO_URI is set, use it directly (recommended for Docker)
    if mongo_uri:
        return mongo_uri
    
    # Fallback: Build from individual components
    host = os.environ.get("MONGO_HOST", "localhost")
    port = os.environ.get("MONGO_PORT", "27017")
    username = os.environ.get("MONGO_ROOT_USERNAME") or os.environ.get("MONGO_USERNAME")
    password = os.environ.get("MONGO_ROOT_PASSWORD") or os.environ.get("MONGO_PASSWORD")
    auth_db = os.environ.get("MONGO_AUTH_DB", "admin")

    if username and password:
        return (
            f"mongodb://{quote_plus(username)}:{quote_plus(password)}"
            f"@{host}:{port}/{db_name}?authSource={quote_plus(auth_db)}"
        )

    return f"mongodb://{host}:{port}/{db_name}"


db_name = os.environ.get("DB_NAME", "ebill_db")
mongo_url = _build_mongo_url(db_name)

# Extract database name from URL if not set in env
if not os.environ.get("DB_NAME"):
    parsed = urlparse(mongo_url)
    db_name = parsed.path.lstrip("/") or "ebill_db"

client = AsyncIOMotorClient(mongo_url)
db = client[db_name]


async def close_db():
    client.close()
