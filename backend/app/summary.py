"""The game summary: 4 to 6 clean lines for the crew's WhatsApp group.

Code collects the facts (score, scorers, assists) from the players' reports.
Gemma turns them into friendly lines, and verify.py checks the numbers."""

import hashlib
import math
from collections import Counter
from html import escape
from urllib.parse import quote

from . import jobs, notify, prompts, telegram, verify
from .db import get_db
from .util import display_name, format_kickoff, now


async def load(game_id) -> tuple[dict, dict, list[dict], dict]:
    """The game, its pitch, its reports (not disputed) and the reporters by id."""
    db = get_db()
    game = await db.games.find_one({"_id": game_id})
    pitch = await db.pitches.find_one({"_id": game["pitch_id"]})
    claims = await db.claims.find(
        {"game_id": game_id, "status": {"$in": ["pending", "confirmed"]}}
    ).sort("created_at", 1).to_list(None)
    users = await db.users.find({"_id": {"$in": [c["user_id"] for c in claims]}}).to_list(None)
    return game, pitch, claims, {u["_id"]: u for u in users}


def fingerprint(claims: list[dict]) -> str:
    """Changes whenever a report is added, replaced or confirmed, so we know
    when the summary is out of date."""
    parts = sorted(f"{c['_id']}:{c['status']}:{c['created_at'].isoformat()}" for c in claims)
    return hashlib.sha1("|".join(parts).encode()).hexdigest()


def summary_key(game: dict, claims: list[dict]) -> str:
    """The fingerprint plus the final score, so entering the score also
    refreshes the summary."""
    result = game.get("result") or {}
    return f"{fingerprint(claims)}:{result.get('us')}-{result.get('them')}"


def enough_reports(game: dict, claims: list[dict]) -> bool:
    """At least half of the players who were in have reported."""
    players_in = sum(1 for invite in game["invites"] if invite["status"] == "in")
    return bool(claims) and len(claims) >= math.ceil(players_in / 2)


def collect_facts(game: dict, pitch: dict, claims: list[dict], users: dict) -> dict:
    """Everything the summary may mention, taken from the reports."""
    def listing(field: str) -> str:
        items = []
        for claim in claims:
            value = claim["stats"].get(field) or 0
            if value > 0 and claim["user_id"] in users:
                pending = "" if claim["status"] == "confirmed" else " (pending)"
                items.append((value, f"{display_name(users[claim['user_id']])} {value}{pending}"))
        return ", ".join(text for _, text in sorted(items, key=lambda item: -item[0]))

    # The score most players reported, written winners first ("5-3").
    scores = Counter(
        (max(s["us"], s["them"]), min(s["us"], s["them"]))
        for s in (claim["stats"].get("score") for claim in claims) if s
    )
    score = "{}-{}".format(*scores.most_common(1)[0][0]) if scores else ""
    if game.get("result"):  # the creator's final score beats what players remember
        score = "{}-{}".format(*sorted([game["result"]["us"], game["result"]["them"]], reverse=True))

    return {
        "pitch": pitch["name"],
        "date": format_kickoff(game["kickoff_at"]),
        "score": score,
        "goals": listing("goals"),
        "assists": listing("assists"),
        "saves": listing("saves"),
    }


def facts_text(facts: dict) -> str:
    lines = [f"Pitch: {facts['pitch']}", f"Date: {facts['date']}"]
    if facts["score"]:
        lines.append(f"Final score: {facts['score']}")
    for label, key in [("Goals", "goals"), ("Assists", "assists"), ("Keeper saves", "saves")]:
        if facts[key]:
            lines.append(f"{label}: {facts[key]}")
    return "\n".join(lines)


def template_summary(facts: dict) -> str:
    """The plain summary used if Gemma fails or invents a number twice."""
    lines = [f"Football at {facts['pitch']}, {facts['date']}."]
    if facts["score"]:
        lines.append(f"Final score: {facts['score']}.")
    for label, key in [("Goals", "goals"), ("Assists", "assists"), ("Saves", "saves")]:
        if facts[key]:
            lines.append(f"{label}: {facts[key]}.")
    lines.append("Well played, everyone. See you at the next one! ⚽")
    return "\n".join(lines)


async def maybe_queue(game_id) -> None:
    """Queue a (new) summary if enough players reported and something changed.
    Called after every new report and every confirmation."""
    db = get_db()
    game, _, claims, _ = await load(game_id)
    if game["status"] == "cancelled" or not enough_reports(game, claims):
        return
    if (game.get("summary") or {}).get("key") == summary_key(game, claims):
        return  # the summary we have is still right
    if await db.jobs.find_one({"type": "summary", "input.game_id": game_id,
                               "status": {"$in": ["queued", "running"]}}):
        return  # one is already on its way
    await jobs.enqueue("summary", {"game_id": game_id})


@jobs.handler("summary")
async def write_summary(job: dict) -> dict:
    game, pitch, claims, users = await load(job["input"]["game_id"])
    facts = collect_facts(game, pitch, claims, users)
    result = await verify.write_with_facts(
        prompts.SUMMARY_SYSTEM, facts_text(facts), lambda: template_summary(facts))

    first_time = not game.get("summary")
    await get_db().games.update_one({"_id": game["_id"]}, {"$set": {"summary": {
        "text": result["text"], "source": result["source"],
        "generated_at": now(), "key": summary_key(game, claims),
    }}})
    if first_time:
        await send_to_players(game, pitch, result["text"])
    return result


async def send_to_players(game: dict, pitch: dict, text: str) -> None:
    """Send the summary on Telegram to everyone who played (the first time only,
    so later updates don't spam)."""
    chats = await notify.chat_ids(notify.ids_with_status(game, "in"))
    if not chats:
        return
    message = (f"📋 <b>{escape(pitch['name'])}</b> · {format_kickoff(game['kickoff_at'])}\n\n"
               f"{escape(text)}")
    buttons = []
    link = telegram.public_url(f"/game/{game['_id']}")
    if link:
        share = f"⭐ {pitch['name']} · {format_kickoff(game['kickoff_at'])}\n\n{text}\n\n{link}"
        buttons = [[("Share to WhatsApp", f"https://wa.me/?text={quote(share)}")],
                   [("Open in Star Boy", link)]]
    await telegram.send_many(list(chats.values()), message, buttons or None)
