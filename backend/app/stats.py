"""Player stats and leaderboards, computed by MongoDB aggregation pipelines."""

from bson import ObjectId

from .db import get_db

# Until claims can be confirmed, every player's numbers are zero.
ZERO_STATS = {"appearances": 0, "goals": 0, "assists": 0, "wins": 0}


async def pitch_players(pitch_id: ObjectId) -> list[dict]:
    """Everyone registered at a pitch, with their stats there."""
    pipeline = [
        {"$match": {"pitch_id": pitch_id}},
        # Join each registration with the user it belongs to.
        {"$lookup": {
            "from": "users",
            "localField": "user_id",
            "foreignField": "_id",
            "as": "user",
        }},
        {"$unwind": "$user"},
        # Keep only the public fields (never the phone number or the PIN hash).
        {"$project": {
            "_id": 0,
            "id": {"$toString": "$user._id"},
            "name": "$user.name",
            "nickname": {"$ifNull": ["$user.nickname", ""]},
            "position": {"$ifNull": ["$user.position", "Anywhere"]},
        }},
        {"$sort": {"name": 1}},
    ]
    players = await get_db().registrations.aggregate(pipeline).to_list(None)
    return [{**player, **ZERO_STATS} for player in players]
