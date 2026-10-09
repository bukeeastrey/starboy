"""Teammates confirm (or dispute) each other's stats. Rules from CLAUDE.md 3.6."""

import math
from datetime import timedelta

from pymongo import ReturnDocument

from .db import get_db
from .util import now

# Small games can't always reach 2 confirmations, so after 72 hours a claim
# with at least one confirm and no disputes counts anyway.
AUTO_CONFIRM_AFTER = timedelta(hours=72)

NUMBERS_FLAG = "numbers_dont_add_up"


# --- The rules (plain functions, easy to test) ----------------------------

def required_confirms(players_in: int) -> int:
    """How many teammates must confirm: at least 2, or a third of the players."""
    return max(2, math.ceil(players_in / 3))


def decide(confirms: int, disputes: int, players_in: int, age: timedelta) -> str:
    """A claim's status from its votes: "pending", "confirmed" or "disputed"."""
    if disputes >= 2 and disputes >= confirms:
        return "disputed"
    if confirms >= required_confirms(players_in) and confirms > disputes:
        return "confirmed"
    if age >= AUTO_CONFIRM_AFTER and confirms >= 1 and disputes == 0:
        return "confirmed"
    return "pending"


def numbers_add_up(claims: list[dict]) -> bool:
    """Do the confirmed goals fit the reported scores? (No AI needed.)

    Players on the same team report the same score ("us 5, them 3"), so
    claims are grouped by the score they report. If a group's goals add up
    to more than that team scored, something is off."""
    groups: dict[tuple, int] = {}
    for claim in claims:
        score = claim["stats"].get("score")
        if score:
            key = (score["us"], score["them"])
            groups[key] = groups.get(key, 0) + (claim["stats"].get("goals") or 0)
    for (us, them), goals in groups.items():
        # In a draw both teams report the same score, so they share one group.
        limit = us + them if us == them else us
        if goals > limit:
            return False
    return True


# --- Using the rules with the database ------------------------------------

def players_in(game: dict) -> int:
    return sum(1 for invite in game["invites"] if invite["status"] == "in")


async def refresh_claim(claim: dict, game: dict) -> str:
    """Work out the claim's status again and save it if it changed."""
    status = decide(len(claim["confirmations"]), len(claim["disputes"]),
                    players_in(game), now() - claim["created_at"])
    if status != claim["status"]:
        update = {"status": status}
        if status == "confirmed":
            update["confirmed_at"] = now()
        await get_db().claims.update_one(
            {"_id": claim["_id"], "status": "pending"}, {"$set": update}
        )
        if status == "confirmed":
            await check_numbers(game["_id"])
        # Tell the player on Telegram. Imported here: notify.py is only
        # needed at this moment, and the rules above stay free of it.
        from . import moments, notify, summary
        try:
            await moments.refresh_game(game["_id"])
            await notify.claim_decided(claim, status)
            await summary.maybe_queue(game["_id"])  # confirmed stats change the summary
        except Exception:
            pass  # a failed message must never undo a confirmation
    return status


async def vote(claim_id, voter_id, choice: str) -> dict | None:
    """Add a confirm or a dispute. Changing your mind moves your vote.
    Only pending claims can be voted on. Returns the updated claim."""
    field, other = ("confirmations", "disputes") if choice == "confirm" else ("disputes", "confirmations")
    claim = await get_db().claims.find_one_and_update(
        {"_id": claim_id, "status": "pending"},
        {"$addToSet": {field: voter_id}, "$pull": {other: voter_id}},
        return_document=ReturnDocument.AFTER,
    )
    if claim:
        game = await get_db().games.find_one({"_id": claim["game_id"]})
        claim["status"] = await refresh_claim(claim, game)
    return claim


async def check_numbers(game_id) -> None:
    """Set or clear the "Numbers no add up 👀" flag on a game."""
    db = get_db()
    confirmed = await db.claims.find({"game_id": game_id, "status": "confirmed"}).to_list(None)
    if numbers_add_up(confirmed):
        await db.games.update_one({"_id": game_id}, {"$pull": {"flags": NUMBERS_FLAG}})
    else:
        await db.games.update_one({"_id": game_id}, {"$addToSet": {"flags": NUMBERS_FLAG}})


async def auto_confirm_due() -> int:
    """Confirm claims that have waited 72 hours with only confirms.
    Run regularly by the scheduler. Returns how many were confirmed."""
    db = get_db()
    due = await db.claims.find({
        "status": "pending",
        "created_at": {"$lte": now() - AUTO_CONFIRM_AFTER},
        "confirmations.0": {"$exists": True},  # at least one confirm
        "disputes": [],
    }).to_list(None)
    count = 0
    for claim in due:
        game = await db.games.find_one({"_id": claim["game_id"]})
        if game and await refresh_claim(claim, game) == "confirmed":
            count += 1
    return count
