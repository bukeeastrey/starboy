"""The connection to MongoDB Atlas (through Motor, the async driver)."""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .config import settings

# One client for the whole app. It is created at startup (see main.py).
_client: AsyncIOMotorClient | None = None


def connect() -> None:
    """Create the client. This does not talk to Atlas yet; the first query does."""
    global _client
    if settings.mongodb_uri:
        _client = AsyncIOMotorClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=5000,  # fail after 5 s rather than hang
            tz_aware=True,  # dates come back as UTC-aware datetimes
        )


def close() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_db() -> AsyncIOMotorDatabase:
    """The Star Boy database. Use it like: get_db().users.find_one(...)"""
    if _client is None:
        raise RuntimeError("MONGODB_URI is not set. Add it to the .env file.")
    return _client[settings.mongodb_db]


async def ping() -> str:
    """Check the database: "ok", "not_configured" or "error"."""
    if _client is None:
        return "not_configured"
    try:
        await _client.admin.command("ping")
        return "ok"
    except Exception:
        return "error"
