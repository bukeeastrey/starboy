"""Games: set one up, invite players, answer the invite, add it to a calendar."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from ..auth import current_user
from ..config import settings
from ..db import get_db
from ..util import WAT, format_kickoff, now, oid, public_user
from .pitches import register_at

router = APIRouter(prefix="/api")


class NewGame(BaseModel):
    date: str  # "2026-10-09", a Lagos date
    time: str  # "17:00", Lagos time
    duration_min: int = 90
    note: str = ""
    invite_user_ids: list[str] = []


class Rsvp(BaseModel):
    status: str  # "in" or "out"


# --- Helpers -------------------------------------------------------------

def game_end(game: dict) -> datetime:
    return game["kickoff_at"] + timedelta(minutes=game["duration_min"])


def game_phase(game: dict) -> str:
    """Where the game is in time: "upcoming", "live" or "finished"."""
    if now() < game["kickoff_at"]:
        return "upcoming"
    return "live" if now() < game_end(game) else "finished"


def invite_of(game: dict, user_id) -> dict | None:
    """This user's entry in the game's invite list, if they have one."""
    for invite in game["invites"]:
        if invite["user_id"] == user_id:
            return invite
    return None


def game_card(game: dict, pitch: dict, me: dict) -> dict:
    """The short version of a game, for lists and the Home screen."""
    mine = invite_of(game, me["_id"])
    return {
        "id": str(game["_id"]),
        "pitch": {"id": str(pitch["_id"]), "name": pitch["name"], "area": pitch.get("area", "")},
        "kickoff_at": game["kickoff_at"].isoformat(),
        "kickoff_label": format_kickoff(game["kickoff_at"]),
        "duration_min": game["duration_min"],
        "note": game.get("note", ""),
        "status": game["status"],
        "phase": game_phase(game),
        "in_count": sum(1 for invite in game["invites"] if invite["status"] == "in"),
        "my_status": mine["status"] if mine else None,
    }


async def cards_for(games: list[dict], me: dict) -> list[dict]:
    """game_card() for several games, loading their pitches in one query."""
    pitch_ids = list({game["pitch_id"] for game in games})
    pitches = await get_db().pitches.find({"_id": {"$in": pitch_ids}}).to_list(None)
    by_id = {pitch["_id"]: pitch for pitch in pitches}
    return [game_card(game, by_id[game["pitch_id"]], me) for game in games]


async def load_game(game_id: str) -> tuple[dict, dict]:
    """The game and its pitch, or a 404 error."""
    db = get_db()
    game = await db.games.find_one({"_id": oid(game_id)})
    if not game:
        raise HTTPException(404, "We can't find that game.")
    pitch = await db.pitches.find_one({"_id": game["pitch_id"]})
    return game, pitch


def site_url(request: Request) -> str:
    """The address players open in their browser (no slash at the end)."""
    return settings.public_base_url.rstrip("/") or str(request.base_url).rstrip("/")


# --- Lists ---------------------------------------------------------------

async def pitch_games(pitch_id, me: dict) -> dict:
    """A pitch's games: the ones still to come, and the last few played."""
    db = get_db()
    # One query for the last 30 days onwards; split by "finished or not" below.
    games = await db.games.find(
        {"pitch_id": pitch_id, "status": {"$ne": "cancelled"},
         "kickoff_at": {"$gte": now() - timedelta(days=30)}}
    ).sort("kickoff_at", 1).to_list(200)
    cards = await cards_for(games, me)
    return {
        "upcoming": [card for card in cards if card["phase"] != "finished"],
        "recent": [card for card in reversed(cards) if card["phase"] == "finished"][:5],
    }


async def my_next_games(me: dict) -> list[dict]:
    """Games I'm invited to (or in) that haven't finished yet. Soonest first."""
    games = await get_db().games.find(
        {"status": "scheduled",
         "kickoff_at": {"$gte": now() - timedelta(hours=6)},
         "invites": {"$elemMatch": {"user_id": me["_id"], "status": {"$in": ["in", "invited"]}}}}
    ).sort("kickoff_at", 1).to_list(20)
    cards = await cards_for(games, me)
    return [card for card in cards if card["phase"] != "finished"][:5]


# --- Create --------------------------------------------------------------

@router.post("/pitches/{pitch_id}/games")
async def create_game(pitch_id: str, body: NewGame, user: dict = Depends(current_user)):
    db = get_db()
    pitch = await db.pitches.find_one({"_id": oid(pitch_id)})
    if not pitch:
        raise HTTPException(404, "We can't find that pitch.")

    # The form sends Lagos date + time; MongoDB stores UTC.
    try:
        local = datetime.strptime(f"{body.date} {body.time}", "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(400, "Pick a date and a kickoff time.")
    kickoff_at = local.replace(tzinfo=WAT).astimezone(timezone.utc)
    if not 10 <= body.duration_min <= 300:
        raise HTTPException(400, "A game lasts between 10 minutes and 5 hours.")

    # Whoever sets up a game plays there, so put them on the pitch's list.
    await register_at(pitch["_id"], user["_id"])

    # Only players registered at this pitch can be invited.
    wanted = [oid(user_id) for user_id in body.invite_user_ids]
    registered = await db.registrations.distinct(
        "user_id", {"pitch_id": pitch["_id"], "user_id": {"$in": wanted}}
    )

    invites = [{"user_id": user["_id"], "status": "in", "responded_at": now()}]
    invites += [
        {"user_id": user_id, "status": "invited", "responded_at": None}
        for user_id in registered if user_id != user["_id"]
    ]
    game = {
        "pitch_id": pitch["_id"],
        "sport": "football",
        "kickoff_at": kickoff_at,
        "duration_min": body.duration_min,
        "note": body.note.strip()[:200],
        "created_by": user["_id"],
        "status": "scheduled",
        "invites": invites,
        "reminders_sent": {},
        "summary": None,
        "flags": [],
        "created_at": now(),
    }
    await db.games.insert_one(game)
    return game_card(game, pitch, user)


# --- One game ------------------------------------------------------------

@router.get("/games/{game_id}")
async def get_game(game_id: str, user: dict = Depends(current_user)):
    game, pitch = await load_game(game_id)

    # Load everyone on the invite list in one query, then group them by answer.
    user_ids = [invite["user_id"] for invite in game["invites"]] + [game["created_by"]]
    users = await get_db().users.find({"_id": {"$in": user_ids}}).to_list(None)
    by_id = {u["_id"]: public_user(u) for u in users}
    players = {"in": [], "invited": [], "out": []}
    for invite in game["invites"]:
        if invite["user_id"] in by_id:
            players[invite["status"]].append(by_id[invite["user_id"]])

    return {
        **game_card(game, pitch, user),
        "created_by": by_id.get(game["created_by"]),
        "is_creator": game["created_by"] == user["_id"],
        "players": players,
    }


@router.post("/games/{game_id}/rsvp")
async def rsvp(game_id: str, body: Rsvp, user: dict = Depends(current_user)):
    """Answer the invite: "in" or "out". Also how someone who got the
    WhatsApp link joins a game they were not on the invite list for."""
    if body.status not in ("in", "out"):
        raise HTTPException(400, "Answer with in or out.")
    game, pitch = await load_game(game_id)
    if game["status"] == "cancelled":
        raise HTTPException(400, "This game was cancelled.")

    db = get_db()
    answer = {"status": body.status, "responded_at": now()}
    if invite_of(game, user["_id"]):
        await db.games.update_one(
            {"_id": game["_id"], "invites.user_id": user["_id"]},
            {"$set": {"invites.$.status": answer["status"],
                      "invites.$.responded_at": answer["responded_at"]}},
        )
    else:
        # Not on the list yet: add them, and register them at the pitch.
        # "$ne" stops a double tap from adding the same player twice.
        await register_at(pitch["_id"], user["_id"])
        await db.games.update_one(
            {"_id": game["_id"], "invites.user_id": {"$ne": user["_id"]}},
            {"$push": {"invites": {
                "user_id": user["_id"], **answer,
                # Joined after kickoff = "I played": someone must confirm it.
                "self_added": game_phase(game) != "upcoming",
            }}},
        )
    return {"my_status": body.status}


@router.post("/games/{game_id}/cancel")
async def cancel_game(game_id: str, user: dict = Depends(current_user)):
    game, _ = await load_game(game_id)
    if game["created_by"] != user["_id"]:
        raise HTTPException(403, "Only the person who set up the game can cancel it.")
    await get_db().games.update_one({"_id": game["_id"]}, {"$set": {"status": "cancelled"}})
    return {"status": "cancelled"}


# --- Calendar file -------------------------------------------------------

def ics_text(text: str) -> str:
    """Escape text for a calendar file."""
    return (text.replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\n", "\\n"))


def ics_time(when: datetime) -> str:
    return when.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


@router.get("/games/{game_id}/calendar.ics")
async def calendar_file(game_id: str, request: Request, user: dict = Depends(current_user)):
    """An .ics file the phone's calendar can open, with two reminders."""
    game, pitch = await load_game(game_id)
    kickoff = game["kickoff_at"]
    link = f"{site_url(request)}/game/{game['_id']}"
    description = "\n".join(part for part in [game.get("note", ""), link] if part)

    # 8 pm Lagos time on the day before the game.
    night_before = (kickoff.astimezone(WAT) - timedelta(days=1)).replace(
        hour=20, minute=0, second=0, microsecond=0)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Star Boy//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{game['_id']}@starboy",
        f"DTSTAMP:{ics_time(now())}",
        f"DTSTART:{ics_time(kickoff)}",
        f"DTEND:{ics_time(game_end(game))}",
        f"SUMMARY:{ics_text('⚽ Football at ' + pitch['name'])}",
        f"LOCATION:{ics_text(', '.join(p for p in [pitch['name'], pitch.get('area', '')] if p))}",
        f"DESCRIPTION:{ics_text(description)}",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        "DESCRIPTION:Football in 2 hours. Lace up!",
        "TRIGGER:-PT2H",
        "END:VALARM",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        "DESCRIPTION:Football tomorrow. You dey come?",
        f"TRIGGER;VALUE=DATE-TIME:{ics_time(night_before)}",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return Response(
        "\r\n".join(lines) + "\r\n",  # calendar files use Windows line endings
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="starboy-game.ics"'},
    )
