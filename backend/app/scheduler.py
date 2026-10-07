"""The reminder scheduler: the part of Star Boy that gets people off the sofa.

Every minute it looks at the games around now and sends whatever is due:
  night_before  8 pm (Lagos) the day before      -> players who are in
  nudge         6 hours before kickoff             -> players who haven't answered
  two_hours     2 hours before kickoff             -> players who are in
  post_game     15 minutes after the final whistle -> "How was your game? 🎙️"

A free server can fall asleep. When it wakes up, anything that was due in the
last 2 hours is still sent (late is better than never); older ones are skipped.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from . import consensus, notify
from .db import get_db
from .util import WAT, now

log = logging.getLogger("starboy.scheduler")

TICK_SECONDS = 60
CATCH_UP = timedelta(hours=2)
PRE_GAME = ("night_before", "nudge", "two_hours")


def due_times(game: dict) -> dict[str, datetime]:
    """When each reminder for this game should go out."""
    kickoff = game["kickoff_at"]
    end = kickoff + timedelta(minutes=game["duration_min"])
    night_before = (kickoff.astimezone(WAT) - timedelta(days=1)).replace(
        hour=20, minute=0, second=0, microsecond=0)
    return {
        "night_before": night_before,
        "nudge": kickoff - timedelta(hours=6),
        "two_hours": kickoff - timedelta(hours=2),
        "post_game": end + timedelta(minutes=15),
    }


def what_to_do(kind: str, due: datetime, game: dict, at: datetime) -> str:
    """"wait", "send" or "skip" for one reminder at time `at`. (Plain function, easy to test.)"""
    if at < due:
        return "wait"
    # A game set up after a pre-game reminder's time never gets that reminder
    # (e.g. a game created an hour before kickoff, or logged after it was played).
    if kind in PRE_GAME and game["created_at"] >= due:
        return "skip"
    # Kickoff has passed: "football in 2 hours" would be nonsense now.
    if kind in PRE_GAME and at >= game["kickoff_at"]:
        return "skip"
    return "send" if at - due <= CATCH_UP else "skip"


async def tick() -> dict:
    """Send everything that is due. Safe to call often, and from two places at
    once: each reminder is "claimed" in the database before it is sent."""
    db = get_db()
    at = now()
    sent = {}

    games = await db.games.find({
        "status": "scheduled",
        # Reminders happen from ~28 h before kickoff to a few hours after it.
        "kickoff_at": {"$gte": at - timedelta(days=1), "$lte": at + timedelta(days=2)},
    }).to_list(None)

    for game in games:
        done = game.get("reminders_sent") or {}
        for kind, due in due_times(game).items():
            if kind in done:
                continue
            action = what_to_do(kind, due, game, at)
            if action == "wait":
                continue
            # Claim it: only one caller's update can match "not set yet".
            claimed = await db.games.update_one(
                {"_id": game["_id"], f"reminders_sent.{kind}": {"$exists": False}},
                {"$set": {f"reminders_sent.{kind}": at if action == "send" else "skipped"}},
            )
            if claimed.modified_count and action == "send":
                count = await notify.reminder(kind, game)
                sent[kind] = sent.get(kind, 0) + count
                log.info("Sent %s reminder for game %s to %d players", kind, game["_id"], count)

    # Reports that waited 72 hours with only confirms now count.
    confirmed = await consensus.auto_confirm_due()
    return {"games_checked": len(games), "messages_sent": sent, "auto_confirmed": confirmed}


async def run_forever() -> None:
    """The background loop started with the server."""
    while True:
        try:
            await tick()
        except Exception as error:
            log.error("Scheduler tick failed: %s", type(error).__name__)
        await asyncio.sleep(TICK_SECONDS)
