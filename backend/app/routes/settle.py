""""Settle it": pick two players, get the table now and the verdict in a moment."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import settle
from ..auth import current_user
from ..db import get_db
from ..util import oid, public_user

router = APIRouter(prefix="/api")


class SettleBody(BaseModel):
    player_a: str
    player_b: str
    pitch_id: str
    game_id: str = ""  # empty = this pitch, all time


@router.post("/settle")
async def settle_it(body: SettleBody, me: dict = Depends(current_user)):
    db = get_db()
    if body.player_a == body.player_b:
        raise HTTPException(400, "Pick two different players.")
    user_a = await db.users.find_one({"_id": oid(body.player_a)})
    user_b = await db.users.find_one({"_id": oid(body.player_b)})
    pitch = await db.pitches.find_one({"_id": oid(body.pitch_id)})
    if not user_a or not user_b or not pitch:
        raise HTTPException(404, "We can't find that player or pitch.")

    game = None
    if body.game_id:
        game = await db.games.find_one({"_id": oid(body.game_id), "pitch_id": pitch["_id"]})
        if not game:
            raise HTTPException(404, "We can't find that game.")

    # The table comes back now; Gemma's verdict comes from the job queue.
    result = await settle.begin(user_a, user_b, pitch, game, asked_by=me["_id"])
    return {**result, "players": {"a": public_user(user_a), "b": public_user(user_b)}}
