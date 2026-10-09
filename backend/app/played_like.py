""""You played like…": after a report, Star Boy says which legend you resembled.

The code picks the legend from the stats (so it is always earned by the
numbers). Gemma only writes one short, fun line about it, and any number it
mentions is checked against the report, as everywhere else."""

import random
import re
from html import escape

from . import jobs, notify, prompts, telegram, verify
from .db import get_db
from .util import display_name, stat_line

# Each kind of game has a pool of legends: global greats and Nigerian ones.
# The order is the order they are tried in.
POOLS = [
    ("hat_trick", ["prime Cristiano Ronaldo", "Rashidi Yekini", "Victor Osimhen"]),
    ("brace", ["Nwankwo Kanu", "Thierry Henry"]),
    ("goal_and_assist", ["Lionel Messi", "Jay-Jay Okocha"]),
    ("playmaker", ["Toni Kroos", "Xavi", "Mikel John Obi"]),
    ("wall", ["Paolo Maldini", "Virgil van Dijk", "Taribo West"]),
    ("keeper", ["Vincent Enyeama", "Gianluigi Buffon"]),
]
LEGENDS = dict(POOLS)
ALL_LEGENDS = [name for _, names in POOLS for name in names]

# A quiet game gets a gentle line and no legend. These are fixed, not AI.
QUIET_LINES = [
    "Preseason form 😅. Next week na your week.",
    "Quiet one today. Even legends get days like this.",
    "You kept your powder dry. The pitch owes you one.",
]

# Used straight away, and kept if Gemma fails or gets a number wrong.
TEMPLATE_LINES = {
    "hat_trick": "{goals} goals. The defenders are still looking for you.",
    "brace": "2 goals, calm as you like.",
    "goal_and_assist": "A goal and an assist: you ran the whole show.",
    "playmaker": "{assists} assists. Everything good went through you.",
    "wall": "Nothing got past you today. Nothing.",
    "keeper": "Safe hands. The goal was locked.",
}


def kind_of_game(stats: dict) -> str:
    """Which pool a report belongs to. Plain rules, first match wins."""
    goals = stats.get("goals") or 0
    assists = stats.get("assists") or 0
    if goals >= 3:
        return "hat_trick"
    if goals == 2:
        return "brace"
    if goals >= 1 and assists >= 1:
        return "goal_and_assist"
    if assists >= 2:
        return "playmaker"
    if stats.get("defending") == "6+":
        return "wall"
    if (stats.get("saves") or 0) >= 4 or stats.get("clean_sheet") is True:
        return "keeper"
    return "quiet"


def pick(stats: dict, avoid: str | None = None, rng=random) -> dict:
    """Choose the legend (at random within the pool, but not the same one as
    last time) and a first line. Returns {"kind", "name", "line", "source"}."""
    kind = kind_of_game(stats)
    if kind == "quiet":
        return {"kind": kind, "name": None, "line": rng.choice(QUIET_LINES), "source": "template"}
    pool = [name for name in LEGENDS[kind] if name != avoid] or LEGENDS[kind]
    line = TEMPLATE_LINES[kind].format(goals=stats.get("goals") or 0, assists=stats.get("assists") or 0)
    return {"kind": kind, "name": rng.choice(pool), "line": line, "source": "template"}


def line_is_ok(line: str, name: str) -> bool:
    """One short line, about this legend and no other."""
    if not line or "\n" in line.strip() or len(line) > 160:
        return False
    for other in ALL_LEGENDS:
        surname = other.split()[-1]  # "Henry", "Okocha", "Dijk"...
        if surname.lower() in name.lower():
            continue  # that's the legend we picked
        if re.search(rf"\b{re.escape(surname)}\b", line, flags=re.IGNORECASE):
            return False
    return True


def facts_text(player_name: str, played_like: dict, stats: dict) -> str:
    """What Gemma gets: who, which legend, and the report's numbers."""
    return (f"Player: {player_name}\n"
            f"Played like: {played_like['name']}\n"
            f"Their game today: {stat_line({**stats, 'result': None})}")


async def choose_for(claim: dict) -> dict:
    """Pick for a new report and save it on the claim. If a legend was picked,
    queue the job that lets Gemma write a better line."""
    db = get_db()
    previous = await db.claims.find_one(
        {"user_id": claim["user_id"], "_id": {"$ne": claim["_id"]}, "played_like.name": {"$ne": None}},
        sort=[("created_at", -1)],
    )
    chosen = pick(claim["stats"], avoid=previous and previous["played_like"]["name"])
    await db.claims.update_one({"_id": claim["_id"]}, {"$set": {"played_like": chosen}})
    if chosen["name"]:
        await jobs.enqueue("played_like", {"claim_id": claim["_id"], "user_id": claim["user_id"]})
    else:
        await tell_player(claim, chosen)
    return chosen


@jobs.handler("played_like")
async def write_line(job: dict) -> dict:
    db = get_db()
    claim = await db.claims.find_one({"_id": job["input"]["claim_id"]})
    if not claim or not (claim.get("played_like") or {}).get("name"):
        return {"skipped": True}  # the report was replaced in the meantime
    played_like = claim["played_like"]
    user = await db.users.find_one({"_id": claim["user_id"]})

    result = await verify.write_with_facts(
        prompts.PLAYED_LIKE_SYSTEM,
        facts_text(display_name(user), played_like, claim["stats"]),
        lambda: played_like["line"],
        max_tokens=60,
        also_check=lambda text: line_is_ok(text, played_like["name"]),
    )
    played_like = {**played_like, "line": result["text"].strip().strip('"“”'), "source": result["source"]}
    await db.claims.update_one({"_id": claim["_id"]}, {"$set": {"played_like": played_like}})
    await tell_player(claim, played_like)
    return played_like


def headline(played_like: dict) -> str:
    """'You played like Nwankwo Kanu', or a softer title for a quiet game."""
    return f"You played like {played_like['name']}" if played_like["name"] else "Quiet game"


async def tell_player(claim: dict, played_like: dict) -> None:
    """Send it to the player on Telegram."""
    chats = await notify.chat_ids([claim["user_id"]])
    for chat_id in chats.values():
        await telegram.send(chat_id, f"⭐ <b>{escape(headline(played_like))}</b>\n{escape(played_like['line'])}")
