""""Settle it": pick two players, get the table now and the verdict in a moment."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import jobs, settle
from ..auth import current_user
from ..db import get_db
from ..util import format_kickoff, oid, public_user

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
    scope = f"{pitch['name']}, all time"
    if body.game_id:
        game = await db.games.find_one({"_id": oid(body.game_id), "pitch_id": pitch["_id"]})
        if not game:
            raise HTTPException(404, "We can't find that game.")
        scope = f"{pitch['name']}, {format_kickoff(game['kickoff_at'])}"

    result = await settle.compare(user_a, user_b, pitch, game)
    players = {"a": public_user(user_a), "b": public_user(user_b)}
    if not result["enough"]:
        return {"enough": False, "message": settle.NOT_ENOUGH, "players": players, "scope": scope}

    # The table is ready now; Gemma's verdict comes from the job queue.
    names = result["names"]
    job_id = await jobs.enqueue("verdict", {
        "user_id": me["_id"],
        "facts": settle.facts_text(names["a"], names["b"], scope, result["table"]),
        "fallback": result["fallback"],
        # None = a draw. The job checks that Gemma's verdict names this player.
        "winner_name": names.get(result["winner"]),
        # For checking that each number is given to the right player.
        "names": names,
        "table": result["table"],
        # For the "Settled" moment on the pitch page.
        "pitch_id": pitch["_id"],
        "a_id": user_a["_id"],
        "b_id": user_b["_id"],
        "winner": result["winner"],
        "all_time": game is None,
    })
    return {"enough": True, "players": players, "names": names, "scope": scope,
            "table": result["table"], "winner": result["winner"], "job_id": job_id}
