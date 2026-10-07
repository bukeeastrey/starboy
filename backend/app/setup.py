"""Things done once when the server starts: indexes and the first pitches."""

from .db import get_db
from .util import now

# Shown until real pitches are added. Only inserted when there are no pitches.
DEFAULT_PITCHES = [
    {"name": "Parklane Football Pitch", "area": "Parklane"},
    {"name": "Estate Field", "area": "Placeholder: edit me"},
    {"name": "School Pitch", "area": "Placeholder: edit me"},
]


async def ensure_indexes() -> None:
    """Create the indexes (MongoDB skips the ones that already exist)."""
    db = get_db()
    await db.users.create_index("phone", unique=True)
    await db.users.create_index("telegram_chat_id", sparse=True)
    # TTL indexes: MongoDB deletes these documents itself once "expires_at" passes.
    await db.link_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.bot_state.create_index("expires_at", expireAfterSeconds=0)
    await db.registrations.create_index([("pitch_id", 1), ("user_id", 1)], unique=True)
    await db.registrations.create_index("user_id")
    await db.games.create_index([("pitch_id", 1), ("kickoff_at", 1)])
    await db.games.create_index("invites.user_id")
    # One report per player per game (the first field also serves "by game").
    await db.claims.create_index([("game_id", 1), ("user_id", 1)], unique=True)
    await db.claims.create_index([("user_id", 1), ("status", 1)])


async def seed_pitches() -> None:
    db = get_db()
    if await db.pitches.count_documents({}) == 0:
        await db.pitches.insert_many([
            {**pitch, "maps_url": "", "sport": "football",
             "created_by": None, "created_at": now()}
            for pitch in DEFAULT_PITCHES
        ])
