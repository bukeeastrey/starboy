"""Pitches: list them, add one, register at one, see who plays there."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pymongo.errors import DuplicateKeyError

from .. import stats
from ..auth import current_user
from ..db import get_db
from ..util import now, oid

router = APIRouter(prefix="/api")


class NewPitch(BaseModel):
    name: str
    area: str = ""
    maps_url: str = ""


def pitch_view(pitch: dict) -> dict:
    return {
        "id": str(pitch["_id"]),
        "name": pitch["name"],
        "area": pitch.get("area", ""),
        "maps_url": pitch.get("maps_url", ""),
        "player_count": pitch.get("player_count", 0),
        "registered": pitch.get("registered", False),
    }


async def pitches_for(user: dict, only_mine: bool = False) -> list[dict]:
    """All pitches with their player count and whether this user plays there."""
    pipeline = [
        {"$match": {"sport": "football"}},
        {"$lookup": {
            "from": "registrations",
            "localField": "_id",
            "foreignField": "pitch_id",
            "as": "regs",
        }},
        {"$addFields": {
            "player_count": {"$size": "$regs"},
            "registered": {"$in": [user["_id"], "$regs.user_id"]},
        }},
        {"$project": {"regs": 0}},
        {"$sort": {"player_count": -1, "name": 1}},
    ]
    if only_mine:
        pipeline.insert(-1, {"$match": {"registered": True}})
    pitches = await get_db().pitches.aggregate(pipeline).to_list(None)
    return [pitch_view(pitch) for pitch in pitches]


@router.get("/pitches")
async def list_pitches(user: dict = Depends(current_user)):
    return await pitches_for(user)


@router.post("/pitches")
async def add_pitch(body: NewPitch, user: dict = Depends(current_user)):
    name = body.name.strip()
    maps_url = body.maps_url.strip()
    if len(name) < 3:
        raise HTTPException(400, "Give the pitch a name.")
    if maps_url and not maps_url.startswith(("https://", "http://")):
        raise HTTPException(400, "The map link should start with https://")

    pitch = {
        "name": name[:80],
        "area": body.area.strip()[:200],
        "maps_url": maps_url[:500],
        "sport": "football",
        "created_by": user["_id"],
        "created_at": now(),
    }
    await get_db().pitches.insert_one(pitch)
    return pitch_view(pitch)


@router.get("/pitches/{pitch_id}")
async def get_pitch(pitch_id: str, user: dict = Depends(current_user)):
    db = get_db()
    pitch = await db.pitches.find_one({"_id": oid(pitch_id)})
    if not pitch:
        raise HTTPException(404, "We can't find that pitch.")

    # Imported here because games.py also imports from this file.
    from .games import pitch_games

    players = await stats.pitch_players(pitch["_id"])
    my_id = str(user["_id"])
    return {
        **pitch_view(pitch),
        "player_count": len(players),
        "registered": any(player["id"] == my_id for player in players),
        "players": players,
        "games": await pitch_games(pitch["_id"], user),
    }


@router.post("/pitches/{pitch_id}/register")
async def register(pitch_id: str, user: dict = Depends(current_user)):
    db = get_db()
    pitch = await db.pitches.find_one({"_id": oid(pitch_id)})
    if not pitch:
        raise HTTPException(404, "We can't find that pitch.")
    await register_at(pitch["_id"], user["_id"])
    return {"registered": True}


async def register_at(pitch_id, user_id) -> None:
    """Put a user on a pitch's player list (fine if they are already on it)."""
    try:
        await get_db().registrations.insert_one(
            {"pitch_id": pitch_id, "user_id": user_id, "created_at": now()}
        )
    except DuplicateKeyError:
        pass
