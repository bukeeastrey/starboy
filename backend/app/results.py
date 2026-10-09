"""Things about a game that belong to the whole game, not to one player's report:
the final score (entered once, by whoever set the game up), who was on which
side, and the Man of the Match vote."""

from collections import Counter

from .db import get_db
from .util import now

# The "blocks + tackles" answer is a bucket, not an exact count. For adding
# up ("The Wall" leaderboard) each bucket counts as its middle value.
DEFENDING_BUCKETS = ("0", "1-2", "3-5", "6+")
DEFENDING_MIDPOINT = {"0": 0, "1-2": 1.5, "3-5": 4, "6+": 7}
HIGH_DEFENDING = "6+"


# --- The final score -------------------------------------------------------

def result_for(game: dict, user_id, stats: dict | None = None) -> tuple[str | None, dict | None]:
    """How the game went for ONE player: ("won" | "lost" | "draw" | None, score).

    The score comes from the game (entered by its creator) when there is one.
    `game["result"]` is {"us", "them", "team_a"}: the score from the creator's
    side, and the players on that side. Everyone else was on the other side.
    Without it, we fall back to what the player said in their own report."""
    result = game.get("result")
    if not result:
        stats = stats or {}
        return stats.get("result"), stats.get("score")

    on_creators_side = user_id in result.get("team_a", [])
    us, them = (result["us"], result["them"]) if on_creators_side else (result["them"], result["us"])
    outcome = "won" if us > them else "lost" if us < them else "draw"
    return outcome, {"us": us, "them": them}


async def set_result(game: dict, us: int, them: int, team_a: list) -> dict:
    """Save the final score and the creator's side. Returns the saved result."""
    in_ids = {invite["user_id"] for invite in game["invites"] if invite["status"] == "in"}
    # The creator is always on their own side; only players who were in count.
    side = [uid for uid in dict.fromkeys([game["created_by"], *team_a]) if uid in in_ids]
    result = {"us": us, "them": them, "team_a": side, "entered_at": now()}
    await get_db().games.update_one({"_id": game["_id"]}, {"$set": {"result": result}})
    return result


# --- Man of the Match ------------------------------------------------------

def motm_winner(claims: list[dict]):
    """The user id with the most MOTM votes, or None.

    Majority wins: one player must have strictly more votes than anyone else.
    A tie means nobody has won it (yet)."""
    votes = Counter(claim["motm_vote_id"] for claim in claims
                    if claim.get("motm_vote_id") and claim["status"] != "disputed")
    ranked = votes.most_common(2)
    if not ranked:
        return None
    if len(ranked) == 2 and ranked[0][1] == ranked[1][1]:
        return None
    return ranked[0][0]
