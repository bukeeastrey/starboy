"""Everything Star Boy tells players on Telegram: invites, reminders, the
post-game question, "please confirm" requests. If the bot is off, or a player
hasn't connected Telegram, these functions quietly do nothing."""

import logging
from datetime import timedelta
from html import escape

from . import telegram
from .db import get_db
from .util import WAT, display_name, format_kickoff, format_time, now, stat_line

log = logging.getLogger("starboy.notify")

# After the post-game question, a voice note counts as the answer for this long.
AWAITING_REPORT_FOR = timedelta(hours=48)


# --- Helpers -------------------------------------------------------------

async def chat_ids(user_ids: list) -> dict:
    """{user_id: telegram chat id} for the players who connected Telegram."""
    if not telegram.enabled() or not user_ids:
        return {}
    users = await get_db().users.find(
        {"_id": {"$in": list(user_ids)}, "telegram_chat_id": {"$ne": None}}
    ).to_list(None)
    return {u["_id"]: u["telegram_chat_id"] for u in users if u.get("telegram_chat_id")}


def ids_with_status(game: dict, status: str) -> list:
    return [invite["user_id"] for invite in game["invites"] if invite["status"] == status]


def rsvp_buttons(game_id) -> list[list[tuple[str, str]]]:
    """I'm in ✅ / Can't make it ❌ (+ a link to the game when we have a public address)."""
    rows = [[("I'm in ✅", f"r:i:{game_id}"), ("Can't make it ❌", f"r:o:{game_id}")]]
    link = telegram.public_url(f"/game/{game_id}")
    if link:
        rows.append([("Open game", link)])
    return rows


def open_button(path: str, label: str = "Open in Star Boy") -> list[list[tuple[str, str]]] | None:
    link = telegram.public_url(path)
    return [[(label, link)]] if link else None


async def pitch_of(game: dict) -> dict:
    return await get_db().pitches.find_one({"_id": game["pitch_id"]})


async def await_report(chat_id: int, game_id) -> None:
    """Remember that this chat's next voice note is about this game."""
    await get_db().bot_state.update_one(
        {"_id": chat_id},
        {"$set": {"awaiting_report_game_id": game_id, "expires_at": now() + AWAITING_REPORT_FOR},
         "$unset": {"pending": ""}},
        upsert=True,
    )


def how_was_your_game(pitch: dict) -> str:
    return f"How was your game at <b>{escape(pitch['name'])}</b> today? ⚽"


def report_buttons(game_id) -> list[list[tuple[str, str]]]:
    """Two ways to report: tap through a few buttons, or just talk."""
    return [[("Tap my stats 📋", f"ts:{game_id}")],
            [("Send a voice note 🎙️", f"vn:{game_id}")]]


async def ask_creator_for_score(game: dict, pitch: dict) -> None:
    """The final score is entered once, by whoever set the game up."""
    if game.get("result"):
        return
    chats = await chat_ids([game["created_by"]])
    for chat_id in chats.values():
        await get_db().bot_state.update_one(
            {"_id": chat_id},
            {"$set": {"awaiting_score_game_id": game["_id"],
                      "expires_at": now() + AWAITING_REPORT_FOR}},
            upsert=True,
        )
        await telegram.send(
            chat_id,
            f"You set up the game at <b>{escape(pitch['name'])}</b>. What was the final score?\n"
            "Reply like <b>5-3</b>, your side first.",
            open_button(f"/game/{game['_id']}", "Or enter it on the web"))


# --- Invites and cancellations ---------------------------------------------

async def invites(game: dict, pitch: dict, inviter: dict, user_ids: list) -> None:
    chats = await chat_ids(user_ids)
    text = (f"⚽ <b>{escape(display_name(inviter))}</b> invited you to football at "
            f"<b>{escape(pitch['name'])}</b>, {format_kickoff(game['kickoff_at'])}.")
    if game.get("note"):
        text += f"\n📝 {escape(game['note'])}"
    text += "\n\nYou dey come?"
    await telegram.send_many(list(chats.values()), text, rsvp_buttons(game["_id"]))


async def cancelled(game: dict, pitch: dict) -> None:
    chats = await chat_ids(ids_with_status(game, "in"))
    text = (f"❌ The game at <b>{escape(pitch['name'])}</b> on "
            f"{format_kickoff(game['kickoff_at'])} was cancelled.")
    await telegram.send_many(list(chats.values()), text)


# --- Reminders (CLAUDE.md 3.4) ---------------------------------------------

async def reminder(kind: str, game: dict) -> int:
    """Send one kind of reminder for a game. Returns how many messages went out."""
    pitch = await pitch_of(game)
    name = escape(pitch["name"])
    in_ids = ids_with_status(game, "in")
    in_count = len(in_ids)
    game_id = game["_id"]

    if kind == "night_before":
        chats = await chat_ids(in_ids)
        text = f"Tomorrow: football at <b>{name}</b>, {format_time(game['kickoff_at'])}. You dey come? 🔥"
        return await telegram.send_many(list(chats.values()), text, rsvp_buttons(game_id))

    if kind == "two_hours":
        chats = await chat_ids(in_ids)
        text = (f"Football in 2 hours at <b>{name}</b>. "
                f"{in_count} {'player' if in_count == 1 else 'players'} in. Lace up 👟")
        return await telegram.send_many(list(chats.values()), text,
                                        open_button(f"/game/{game_id}", "Open game"))

    if kind == "nudge":
        chats = await chat_ids(ids_with_status(game, "invited"))
        text = (f"<b>{name}</b> needs you. {in_count} in so far for "
                f"{format_kickoff(game['kickoff_at'])}. You dey come?")
        return await telegram.send_many(list(chats.values()), text, rsvp_buttons(game_id))

    if kind == "post_game":
        # Don't ask players who already told Star Boy about this game.
        reported = await get_db().claims.distinct("user_id", {"game_id": game_id})
        chats = await chat_ids([uid for uid in in_ids if uid not in reported])
        for chat_id in chats.values():
            # A voice note sent straight away, without tapping a button, still works.
            await await_report(chat_id, game_id)
        sent = await telegram.send_many(list(chats.values()), how_was_your_game(pitch),
                                        report_buttons(game_id))
        await ask_creator_for_score(game, pitch)
        return sent

    return 0


# --- Confirmations -----------------------------------------------------------

def vote_buttons(claim_id) -> list[list[tuple[str, str]]]:
    return [[("Confirm ✅", f"v:c:{claim_id}"), ("Dispute ❌", f"v:d:{claim_id}")]]


async def claim_to_teammates(claim: dict, game: dict, claimant: dict) -> None:
    """Ask everyone else who was in the game to confirm a new report."""
    try:
        others = [uid for uid in ids_with_status(game, "in") if uid != claimant["_id"]]
        chats = await chat_ids(others)
        if not chats:
            return
        pitch = await pitch_of(game)
        day = game["kickoff_at"].astimezone(WAT).strftime("%A")
        text = (f"From {day}'s game at <b>{escape(pitch['name'])}</b>:\n"
                f"<b>{escape(display_name(claimant))}</b> says {escape(stat_line(claim['stats']))}.")
        if claim["stats"].get("highlight"):
            text += f"\n<i>“{escape(claim['stats']['highlight'])}”</i>"
        text += "\n\nNa true?"
        await telegram.send_many(list(chats.values()), text, vote_buttons(claim["_id"]))
    except Exception:
        log.exception("Could not ask teammates to confirm a report")


async def claim_decided(claim: dict, status: str) -> None:
    """Tell a player their report was confirmed (or disputed)."""
    chats = await chat_ids([claim["user_id"]])
    if not chats:
        return
    line = escape(stat_line(claim["stats"]))
    if status == "confirmed":
        text = f"Your teammates confirmed your stats ✅\n{line}\nE don enter the leaderboard. 🏆"
        buttons = open_button(f"/game/{claim['game_id']}", "Open game")
    else:
        text = (f"Your teammates disputed your report ❌\n{line}\n"
                "Send me a new voice note with the right numbers.")
        buttons = None
        await await_report(chats[claim["user_id"]], claim["game_id"])
    await telegram.send(chats[claim["user_id"]], text, buttons)
