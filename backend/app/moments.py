"""Moments: the highlights feed on a pitch page.

A moment is a small card made by CODE from confirmed stats: a hat-trick, a
clean sheet, a man of the match, a 10th game, a new Golden Boot leader, a
"Settle it" verdict. No AI writes these: every word comes from a template
and every number from the database.

Each moment has a unique `key`, so working them out again (after another
teammate confirms, say) never makes a duplicate."""

from datetime import timedelta

from bson import ObjectId
from pymongo import ReturnDocument

from . import photos, results, stats
from .db import get_db
from .util import display_name, format_kickoff, now, public_user

REACTIONS = {"fire": "🔥", "ball": "⚽", "clap": "👏", "laugh": "😂"}

APPEARANCE_MILESTONES = (10, 25, 50)
GOAL_MILESTONES = (10, 25)
STREAKS = (3, 5, 10)

FEED_SIZE = 12


def ordinal(n: int) -> str:
    """10 -> '10th', 21 -> '21st'."""
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def from_report(claim: dict, name: str) -> list[tuple[str, str, str]]:
    """The moments one confirmed report earns: (kind, title, line).
    Plain rules on the player's own numbers."""
    stats_ = claim["stats"]
    goals = stats_.get("goals") or 0
    found = []
    if goals >= 3:
        title = "Hat-trick" if goals == 3 else f"{goals} goals"
        found.append(("hat_trick", title, f"{name} scored {goals} in one game."))
    elif goals == 2:
        found.append(("brace", "Brace", f"{name} scored 2."))
    if stats_.get("clean_sheet") is True:
        found.append(("clean_sheet", "Clean sheet", f"Nothing got past {name}."))
    if stats_.get("defending") == results.HIGH_DEFENDING:
        found.append(("wall", "The Wall", f"{name} made 6+ blocks and tackles."))
    return found


def milestones(name: str, appearances: int, goals: int, goals_this_game: int) -> list[tuple[str, str, str]]:
    """Milestones reached with this game: (key part, title, line)."""
    found = []
    if appearances in APPEARANCE_MILESTONES:
        found.append((f"app:{appearances}", f"{ordinal(appearances)} game",
                      f"{name} has now played {appearances} games here."))
    for mark in GOAL_MILESTONES:
        # Reached with this game: at or past the mark now, short of it before.
        if goals >= mark > goals - goals_this_game:
            found.append((f"goals:{mark}", f"{mark} goals", f"{name} has scored {goals} goals here."))
    return found


async def save(key: str, pitch_id, kind: str, title: str, line: str, *, user_id=None,
               game_id=None, at=None, game_scoped: bool = False) -> None:
    """Create a moment, or refresh its text if it already exists.
    Reactions and the original time are kept."""
    await get_db().moments.update_one(
        {"key": key},
        {"$set": {"pitch_id": pitch_id, "kind": kind, "title": title, "line": line,
                  "user_id": user_id, "game_id": game_id, "game_scoped": game_scoped},
         "$setOnInsert": {"at": at or now(), "reactions": {name: [] for name in REACTIONS}}},
        upsert=True,
    )


async def refresh_game(game_id) -> None:
    """Work out every moment a game has earned so far. Called whenever a
    report is saved or confirmed, or the final score is entered."""
    db = get_db()
    game = await db.games.find_one({"_id": game_id})
    if not game or game["status"] == "cancelled":
        await db.moments.delete_many({"game_id": game_id, "game_scoped": True})
        return
    pitch_id = game["pitch_id"]
    claims = await db.claims.find({"game_id": game_id, "status": {"$ne": "disputed"}}).to_list(None)
    confirmed = [claim for claim in claims if claim["status"] == "confirmed"]
    user_ids = {claim["user_id"] for claim in claims} | {c["motm_vote_id"] for c in claims if c.get("motm_vote_id")}
    users = {u["_id"]: u for u in await db.users.find({"_id": {"$in": list(user_ids)}}).to_list(None)}
    at = game["kickoff_at"] + timedelta(minutes=game["duration_min"])

    # 1. Moments that belong to this one game. If a report is later edited or
    #    disputed, the ones it no longer earns are removed.
    keep = []
    for claim in confirmed:
        user = users.get(claim["user_id"])
        if not user:
            continue
        for kind, title, line in from_report(claim, display_name(user)):
            key = f"game:{game_id}:{kind}:{user['_id']}"
            keep.append(key)
            await save(key, pitch_id, kind, title, line, user_id=user["_id"], game_id=game_id,
                       at=at, game_scoped=True)
    winner = results.motm_winner(claims)
    if winner in users:
        key = f"game:{game_id}:motm"
        keep.append(key)
        await save(key, pitch_id, "motm", "Man of the match",
                   f"{display_name(users[winner])}, voted by the players.",
                   user_id=winner, game_id=game_id, at=at + timedelta(seconds=1), game_scoped=True)
    await db.moments.delete_many({"game_id": game_id, "game_scoped": True, "key": {"$nin": keep}})

    # 2. Moments about a player's record at this pitch. Once earned, they stay.
    if not confirmed:
        return
    totals = await stats.totals_by_player({"game.pitch_id": pitch_id})
    for claim in confirmed:
        user = users.get(claim["user_id"])
        mine = totals.get(claim["user_id"])
        if not user or not mine:
            continue
        name = display_name(user)
        for part, title, line in milestones(name, mine["appearances"], mine["goals"],
                                            claim["stats"].get("goals") or 0):
            await save(f"milestone:{pitch_id}:{user['_id']}:{part}", pitch_id, "milestone", title, line,
                       user_id=user["_id"], game_id=game_id, at=at + timedelta(seconds=2))
        streak = await win_streak(user["_id"], pitch_id)
        if streak in STREAKS:
            await save(f"streak:{pitch_id}:{user['_id']}:{streak}:{game_id}", pitch_id, "streak",
                       f"{streak} wins in a row", f"{name} can't stop winning.",
                       user_id=user["_id"], game_id=game_id, at=at + timedelta(seconds=3))

    # 3. Has the Golden Boot changed hands?
    boards = await stats.leaderboards(pitch_id, limit=2)
    top = boards["golden_boot"]
    # A clear leader only: level on goals with second place is not a lead.
    if top and (len(top) == 1 or top[0]["goals"] > top[1]["goals"]):
        leader_id = top[0]["id"]
        pitch = await db.pitches.find_one_and_update(
            {"_id": pitch_id}, {"$set": {"golden_boot_leader": leader_id}},
            return_document=ReturnDocument.BEFORE)
        if pitch and pitch.get("golden_boot_leader") != leader_id:
            name = top[0]["nickname"] or top[0]["name"].split()[0]
            first_time = not pitch.get("golden_boot_leader")
            await save(f"boot:{pitch_id}:{leader_id}:{game_id}", pitch_id, "golden_boot",
                       "Golden Boot leader" if first_time else "New Golden Boot leader",
                       f"{name} leads with {top[0]['goals']} goals.",
                       user_id=ObjectId(leader_id), game_id=game_id, at=at + timedelta(seconds=4))


async def win_streak(user_id, pitch_id) -> int:
    """How many of the player's latest confirmed games here they won in a row."""
    from .settle import confirmed_reports, totals  # here: settle.py imports this file's siblings
    return totals(await confirmed_reports(user_id, {"game.pitch_id": pitch_id}))["streak"]


async def add_verdict(pitch_id, winner: dict | None, a: dict, b: dict, text: str) -> None:
    """A "Settle it" verdict becomes a moment (one per pair of players per day)."""
    pair = "-".join(sorted([str(a["_id"]), str(b["_id"])]))
    if winner:
        loser = b if winner["_id"] == a["_id"] else a
        title, user_id = "Settled", winner["_id"]
        line = f"{display_name(winner)} over {display_name(loser)}. {text}"
    else:
        title, user_id = "Settled: a draw", None
        line = f"{display_name(a)} and {display_name(b)} can't be split. {text}"
    await save(f"verdict:{pitch_id}:{pair}:{now():%Y-%m-%d}", pitch_id, "verdict", title, line[:400],
               user_id=user_id)


async def feed(pitch_id, me: dict) -> list[dict]:
    """The newest moments at a pitch, ready for the app."""
    db = get_db()
    moments = await db.moments.find({"pitch_id": pitch_id}).sort("at", -1).to_list(FEED_SIZE)
    users = {u["_id"]: u for u in await db.users.find(
        {"_id": {"$in": [m["user_id"] for m in moments if m.get("user_id")]}}).to_list(None)}
    # A photo from the same match, when the game has one.
    pictures = await photos.for_games([m["game_id"] for m in moments if m.get("game_id")])

    # Several moments from one game each get a different photo from it.
    used: dict = {}

    def picture_for(game_id):
        available = pictures.get(game_id)
        if not available:
            return None
        used[game_id] = used.get(game_id, -1) + 1
        return available[used[game_id] % len(available)]

    return [
        {
            "id": str(moment["_id"]),
            "kind": moment["kind"],
            "title": moment["title"],
            "line": moment["line"],
            "player": public_user(users[moment["user_id"]]) if moment.get("user_id") in users else None,
            "game_id": str(moment["game_id"]) if moment.get("game_id") else None,
            "when": format_kickoff(moment["at"]).split(",")[0],  # "Fri 9 Oct"
            "photo": picture_for(moment.get("game_id")),
            "reactions": {name: len(moment["reactions"].get(name, [])) for name in REACTIONS},
            "my_reaction": next((name for name in REACTIONS
                                 if me["_id"] in moment["reactions"].get(name, [])), None),
        }
        for moment in moments
    ]


async def react(moment_id, user_id, reaction: str) -> dict | None:
    """One reaction per player per moment. Tapping the one you already gave
    takes it back; tapping another moves yours."""
    db = get_db()
    moment = await db.moments.find_one({"_id": moment_id})
    if not moment:
        return None
    already = user_id in moment["reactions"].get(reaction, [])
    # Take this player out of all four, then (unless undoing) put them in one.
    await db.moments.update_one(
        {"_id": moment_id}, {"$pull": {f"reactions.{name}": user_id for name in REACTIONS}})
    if not already:
        await db.moments.update_one({"_id": moment_id}, {"$addToSet": {f"reactions.{reaction}": user_id}})
    updated = await db.moments.find_one({"_id": moment_id})
    return {"reactions": {name: len(updated["reactions"].get(name, [])) for name in REACTIONS},
            "my_reaction": None if already else reaction}
