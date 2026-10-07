"""A player's public profile, and voting on teammates' reports."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import consensus, stats
from ..auth import current_user
from ..db import get_db
from ..util import format_kickoff, oid, public_user
from .games import invite_of

router = APIRouter(prefix="/api")


class Vote(BaseModel):
    vote: str  # "confirm" or "dispute"


@router.get("/players/{user_id}")
async def player_profile(user_id: str, me: dict = Depends(current_user)):
    db = get_db()
    user = await db.users.find_one({"_id": oid(user_id)})
    if not user:
        raise HTTPException(404, "We can't find that player.")

    # The last 10 games they reported on, newest first.
    recent = await db.claims.aggregate([
        {"$match": {"user_id": user["_id"], "status": {"$in": ["pending", "confirmed"]}}},
        {"$lookup": {"from": "games", "localField": "game_id", "foreignField": "_id", "as": "game"}},
        {"$unwind": "$game"},
        {"$match": {"game.status": {"$ne": "cancelled"}}},
        {"$sort": {"game.kickoff_at": -1}},
        {"$limit": 10},
        {"$lookup": {"from": "pitches", "localField": "game.pitch_id", "foreignField": "_id", "as": "pitch"}},
        {"$unwind": "$pitch"},
    ]).to_list(None)

    # Pitches they're registered at (for "Settle it" and the profile header).
    registrations = await db.registrations.find({"user_id": user["_id"]}).to_list(None)
    pitches = await db.pitches.find(
        {"_id": {"$in": [r["pitch_id"] for r in registrations]}}
    ).to_list(None)

    return {
        **public_user(user),
        "is_me": user["_id"] == me["_id"],
        "pitch_stats": await stats.player_pitch_stats(user["_id"]),
        "pitches": [{"id": str(p["_id"]), "name": p["name"]} for p in pitches],
        "recent_games": [
            {
                "game_id": str(claim["game"]["_id"]),
                "pitch_name": claim["pitch"]["name"],
                "kickoff_label": format_kickoff(claim["game"]["kickoff_at"]),
                "stats": claim["stats"],
                "status": claim["status"],
            }
            for claim in recent
        ],
    }


@router.post("/claims/{claim_id}/vote")
async def vote_on_claim(claim_id: str, body: Vote, me: dict = Depends(current_user)):
    """Confirm ✅ or dispute ❌ a teammate's report."""
    if body.vote not in ("confirm", "dispute"):
        raise HTTPException(400, "Vote confirm or dispute.")
    db = get_db()
    claim = await db.claims.find_one({"_id": oid(claim_id)})
    if not claim:
        raise HTTPException(404, "We can't find that report.")
    if claim["user_id"] == me["_id"]:
        raise HTTPException(400, "You can't confirm your own report 😄")
    if claim["status"] != "pending":
        raise HTTPException(400, f"This report is already {claim['status']}.")

    game = await db.games.find_one({"_id": claim["game_id"]})
    invite = invite_of(game, me["_id"])
    if not invite or invite["status"] != "in":
        raise HTTPException(403, "Only players who were in this game can confirm reports.")

    updated = await consensus.vote(claim["_id"], me["_id"], body.vote)
    return {"status": updated["status"] if updated else claim["status"]}
