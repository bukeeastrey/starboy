"""The Telegram bot's brain: what to do with each message and button tap.

Telegram sends "updates". An update is either a message (text, a command
like /next, or a voice note) or a tap on a button under one of our messages."""

import asyncio
import logging
import uuid
from datetime import timedelta
from html import escape

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException

from . import consensus, jobs, notify, photos, stats, tapflow, telegram
from .config import AUDIO_DIR, settings
from .db import get_db
from .routes.games import game_phase, invite_of, set_rsvp
from .routes.reports import save_claim
from .util import display_name, format_kickoff, now, stat_line

log = logging.getLogger("starboy.bot")

MAX_VOICE_SECONDS = 90
REPORT_WINDOW = timedelta(days=7)  # how far back a game can still be reported

HELP = (
    "<b>Star Boy</b> ⭐ gets you out of your room and onto the pitch.\n\n"
    "/next: your next game\n"
    "/report: tell me how your last game went\n"
    "/leaderboard: top players at your pitch\n"
    "/help: this message\n\n"
    "After a game, send me a <b>voice note</b> about how you played, "
    "or a <b>photo</b> for the match gallery."
)
SORRY = "I couldn't make that out. Try another voice note or type it 🙏"


# --- Entry point -----------------------------------------------------------

async def handle_update(update: dict) -> None:
    """Called for every update, in polling mode and in webhook mode."""
    try:
        if "callback_query" in update:
            await on_tap(update["callback_query"])
        elif "message" in update:
            await on_message(update["message"])
    except Exception:
        log.exception("Could not handle a Telegram update")


async def user_for(chat_id: int) -> dict | None:
    return await get_db().users.find_one({"telegram_chat_id": chat_id})


def site() -> str:
    return settings.public_base_url.rstrip("/") or "the Star Boy web app"


# --- Messages --------------------------------------------------------------

async def on_message(message: dict) -> None:
    chat = message["chat"]
    if chat["type"] != "private":
        return  # voice notes and commands are for the private chat only
    chat_id = chat["id"]
    text = (message.get("text") or "").strip()

    if text.startswith("/start"):
        await on_start(message, text)
        return

    user = await user_for(chat_id)
    if not user:
        await telegram.send(chat_id, f"Welcome to Star Boy! ⭐ Sign up here: {site()}, "
                                     "then tap <b>Connect Telegram</b>.")
        return

    if message.get("photo"):
        await on_photo(user, chat_id, message["photo"])
        return

    voice = message.get("voice") or message.get("audio")
    if voice:
        if voice.get("duration", 0) > MAX_VOICE_SECONDS:
            await telegram.send(chat_id, "That one long o! Keep it under 90 seconds and send again.")
            return
        await on_report(user, chat_id, file_id=voice["file_id"])
    elif text.startswith("/next"):
        await cmd_next(user, chat_id)
    elif text.startswith("/report"):
        await cmd_report(user, chat_id)
    elif text.startswith("/leaderboard"):
        await cmd_leaderboard(user, chat_id)
    elif text.startswith("/"):
        await telegram.send(chat_id, HELP)
    elif text:
        # A typed message can be three things. Try the two specific ones first:
        # the exact number after tapping "4+", or the creator's "5-3" final score.
        if await tapflow.on_number(user, chat_id, text):
            return
        if await tapflow.on_score_text(user, chat_id, text):
            return
        await on_report(user, chat_id, text=text)


async def on_start(message: dict, text: str) -> None:
    """/start <token> connects this chat to a Star Boy account."""
    chat_id = message["chat"]["id"]
    token = text.partition(" ")[2].strip()
    db = get_db()

    if not token:
        user = await user_for(chat_id)
        if user:
            await telegram.send(chat_id, f"You're already connected, {escape(display_name(user))}! ⚽\n\n{HELP}")
        else:
            await telegram.send(chat_id, f"Welcome to Star Boy! ⭐ Sign up here: {site()}, "
                                         "then tap <b>Connect Telegram</b>.")
        return

    # The token was made by the web app for one signed-in user (see routes/telegram.py).
    link = await db.link_tokens.find_one_and_delete({"_id": token, "expires_at": {"$gt": now()}})
    if not link:
        await telegram.send(chat_id, "That link has expired. Open Star Boy and tap "
                                     "<b>Connect Telegram</b> again.")
        return

    # One Telegram chat belongs to one account: disconnect it from any other.
    await db.users.update_many(
        {"telegram_chat_id": chat_id},
        {"$set": {"telegram_chat_id": None, "telegram_username": None}},
    )
    await db.users.update_one({"_id": link["user_id"]}, {"$set": {
        "telegram_chat_id": chat_id,
        "telegram_username": message["from"].get("username"),
        "telegram_linked_at": now(),
    }})
    user = await db.users.find_one({"_id": link["user_id"]})
    await telegram.send(chat_id, f"You're connected, {escape(display_name(user))}! "
                                 "I'll remind you about games at your pitches. ⚽")


# --- Commands --------------------------------------------------------------

async def cmd_next(user: dict, chat_id: int) -> None:
    db = get_db()
    game = await db.games.find_one(
        {"status": "scheduled", "kickoff_at": {"$gte": now()},
         "invites": {"$elemMatch": {"user_id": user["_id"], "status": {"$in": ["in", "invited"]}}}},
        sort=[("kickoff_at", 1)],
    )
    if not game:
        await telegram.send(chat_id, "No game on your list yet. Open Star Boy and set one up! ⚽")
        return
    pitch = await notify.pitch_of(game)
    in_count = len(notify.ids_with_status(game, "in"))
    mine = invite_of(game, user["_id"])["status"]
    text = (f"⚽ <b>{escape(pitch['name'])}</b>\n🗓 {format_kickoff(game['kickoff_at'])}\n"
            f"👥 {in_count} in · " + ("You're in ✅" if mine == "in" else "You never answer o 👀"))
    if game.get("note"):
        text += f"\n📝 {escape(game['note'])}"
    await telegram.send(chat_id, text, notify.rsvp_buttons(game["_id"]))


async def cmd_report(user: dict, chat_id: int) -> None:
    games = await reportable_games(user)
    if not games:
        await telegram.send(chat_id, "I don't see a game from this week to report. "
                                     "Mark yourself “in” on a game first.")
    elif len(games) == 1:
        pitch = await notify.pitch_of(games[0])
        await notify.await_report(chat_id, games[0]["_id"])
        await telegram.send(chat_id, notify.how_was_your_game(pitch),
                            notify.report_buttons(games[0]["_id"]))
    else:
        await telegram.send(chat_id, "Which game?", await game_choice_buttons(games))


async def cmd_leaderboard(user: dict, chat_id: int) -> None:
    db = get_db()
    # "Main pitch" = where they have played most; otherwise where they registered first.
    played = await stats.player_pitch_stats(user["_id"])
    if played:
        pitch_id = ObjectId(played[0]["pitch"]["id"])
    else:
        registration = await db.registrations.find_one({"user_id": user["_id"]}, sort=[("created_at", 1)])
        if not registration:
            await telegram.send(chat_id, "Register at a pitch in Star Boy first. 🏟️")
            return
        pitch_id = registration["pitch_id"]

    pitch = await db.pitches.find_one({"_id": pitch_id})
    boards = await stats.leaderboards(pitch_id, limit=5)
    lines = [f"⭐ <b>{escape(pitch['name'])}</b>"]
    for key, title, stat in [("golden_boot", "👟 Golden Boot", "goals"),
                             ("playmaker", "🎯 Playmaker", "assists"),
                             ("most_consistent", "🏃 Most Consistent", "appearances")]:
        if boards[key]:
            lines.append(f"\n<b>{title}</b>")
            lines += [f"{i}. {escape(row['nickname'] or row['name'])} ({row[stat]})"
                      for i, row in enumerate(boards[key], start=1)]
    if len(lines) == 1:
        lines.append("\nNo confirmed stats yet. Play, report, confirm! ⚽")
    await telegram.send(chat_id, "\n".join(lines), notify.open_button(f"/pitch/{pitch_id}", "Open pitch"))


# --- "How was your game?" ----------------------------------------------------

async def reportable_games(user: dict, only_unreported: bool = True) -> list[dict]:
    """Recent games this player was in (newest first)."""
    db = get_db()
    games = await db.games.find(
        {"status": "scheduled",
         "kickoff_at": {"$gte": now() - REPORT_WINDOW, "$lte": now()},
         "invites": {"$elemMatch": {"user_id": user["_id"], "status": "in"}}}
    ).sort("kickoff_at", -1).to_list(10)
    if only_unreported:
        reported = await db.claims.distinct(
            "game_id", {"user_id": user["_id"], "game_id": {"$in": [g["_id"] for g in games]}})
        games = [g for g in games if g["_id"] not in reported]
    return games


async def game_choice_buttons(games: list[dict]) -> list[list[tuple[str, str]]]:
    rows = []
    for game in games[:5]:
        pitch = await notify.pitch_of(game)
        rows.append([(f"{pitch['name']} · {format_kickoff(game['kickoff_at'])}", f"g:{game['_id']}")])
    return rows


async def on_report(user: dict, chat_id: int, file_id: str | None = None, text: str | None = None) -> None:
    """A voice note or a text arrived. Work out which game it is about."""
    db = get_db()
    state = await db.bot_state.find_one({"_id": chat_id, "expires_at": {"$gt": now()}})
    game = None
    if state and state.get("awaiting_report_game_id"):
        game = await db.games.find_one({"_id": state["awaiting_report_game_id"]})

    if not game:
        games = await reportable_games(user)
        if not games:
            await telegram.send(chat_id, "I don't see a game from this week to report. "
                                         "Try /next to see what's coming up.")
            return
        if len(games) > 1:
            # Keep what they sent, ask which game, continue when they tap (see on_tap).
            await db.bot_state.update_one(
                {"_id": chat_id},
                {"$set": {"pending": {"file_id": file_id, "text": text},
                          "expires_at": now() + notify.AWAITING_REPORT_FOR}},
                upsert=True,
            )
            await telegram.send(chat_id, "Which game is this about?", await game_choice_buttons(games))
            return
        game = games[0]

    await start_report_job(user, chat_id, game, file_id, text)


async def start_report_job(user: dict, chat_id: int, game: dict,
                           file_id: str | None, text: str | None) -> None:
    db = get_db()
    invite = invite_of(game, user["_id"])
    if game["status"] == "cancelled" or game_phase(game) == "upcoming" or not invite or invite["status"] != "in":
        await telegram.send(chat_id, "You can report a game after kickoff, once you're marked “in”.")
        return
    if await db.jobs.find_one({"input.user_id": user["_id"], "status": {"$in": ["queued", "running"]}}):
        await telegram.send(chat_id, "I'm still working on your last one. One moment! ⏳")
        return

    # Answer straight away, so the wait feels natural.
    await telegram.send(chat_id, "Got it 🎧 give me a minute…")

    job_input = {"game_id": game["_id"], "user_id": user["_id"], "telegram_chat_id": chat_id}
    if file_id:
        path = AUDIO_DIR / f"{uuid.uuid4().hex}.audio"
        if not await telegram.download(file_id, path):
            await telegram.send(chat_id, SORRY)
            return
        job_input["audio_path"] = str(path)
    else:
        job_input["text"] = (text or "")[:1000]
    await jobs.enqueue("transcribe_extract", job_input)


@jobs.on_finished
async def reply_when_done(job: dict) -> None:
    """The AI job is finished: send "Here's what I heard" to the player."""
    chat_id = job["input"].get("telegram_chat_id")
    if not chat_id or job["type"] != "transcribe_extract":
        return
    result = job.get("result") or {}
    if job["status"] == "error":
        await telegram.send(chat_id, SORRY)
        return
    if result.get("empty"):
        await telegram.send(chat_id, "I didn't catch that. Try again or type it.")
        return

    game_id = job["input"]["game_id"]
    report = result["stats"]
    lines = ["<b>Here's what I heard</b>", f"<i>“{escape(result['transcript'])}”</i>", "",
             f"⚽ {escape(stat_line(report))}"]
    if report["assisted_players"]:
        lines.append("🎯 Assisted: " + escape(", ".join(p["name"] for p in report["assisted_players"])))
    if result["unclear"]:
        lines.append("🤔 I wasn't sure about: " + escape("; ".join(result["unclear"])))

    buttons = [[("Looks right ✅", f"ok:{job['_id']}")]]
    edit_link = telegram.public_url(f"/game/{game_id}/report?job={job['_id']}")
    if edit_link:
        buttons.append([("Edit on web ✏️", edit_link)])
    else:
        lines += ["", "Something wrong? Send a new voice note, or fix it in the web app."]
    await telegram.send(chat_id, "\n".join(lines), buttons)


# --- Match photos ------------------------------------------------------------

def pick_sizes(sizes: list[dict]) -> tuple[str, str]:
    """Telegram sends each photo in several sizes. Returns the file ids of
    (the mid-size one for the gallery, a small one for thumbnails)."""
    by_size = sorted(sizes, key=lambda s: max(s["width"], s["height"]))
    side = lambda s: max(s["width"], s["height"])  # noqa: E731
    # The biggest one that is still mid-size (500 to 1000 px); if there is no
    # such size, the biggest there is.
    full = next((s for s in reversed(by_size) if 500 <= side(s) <= 1000), by_size[-1])
    thumb = next((s for s in by_size if side(s) >= 300), by_size[-1])
    if side(thumb) > side(full):
        thumb = full
    return full["file_id"], thumb["file_id"]


async def on_photo(user: dict, chat_id: int, sizes: list[dict]) -> None:
    """A photo arrived: put it in the gallery of the game it is from."""
    full_id, thumb_id = pick_sizes(sizes)
    games = await reportable_games(user, only_unreported=False)
    if not games:
        await telegram.send(chat_id, "Nice one! But I don't see a game of yours from this week "
                                     "to put it in. Mark yourself “in” on a game first.")
    elif len(games) == 1:
        await add_match_photo(user, chat_id, games[0], full_id, thumb_id)
    else:
        # Keep the photo's ids, ask which game, continue on the tap.
        await get_db().bot_state.update_one(
            {"_id": chat_id},
            {"$set": {"pending_photo": {"full": full_id, "thumb": thumb_id},
                      "expires_at": now() + notify.AWAITING_REPORT_FOR}},
            upsert=True,
        )
        rows = [[(label, action.replace("g:", "pg:", 1))] for [(label, action)] in await game_choice_buttons(games)]
        await telegram.send(chat_id, "Which game is this photo from?", rows)


async def add_match_photo(user: dict, chat_id: int, game: dict, full_id: str, thumb_id: str) -> None:
    db = get_db()
    if await db.photos.count_documents({"kind": "game", "game_id": game["_id"]}) >= photos.MAX_PER_GAME:
        await telegram.send(chat_id, "That game's gallery is full already.")
        return
    full, thumb = await telegram.fetch(full_id), await telegram.fetch(thumb_id)
    if not full or not thumb:
        await telegram.send(chat_id, "I couldn't get that photo. Send it again?")
        return
    try:
        await photos.save("game", user["_id"], full, thumb, game_id=game["_id"],
                          pitch_id=game["pitch_id"], source="telegram")
    except HTTPException as error:
        await telegram.send(chat_id, str(error.detail))
        return
    pitch = await notify.pitch_of(game)
    await telegram.send(chat_id, f"Added to the gallery for <b>{escape(pitch['name'])}</b>, "
                                 f"{format_kickoff(game['kickoff_at'])}.",
                        notify.open_button(f"/game/{game['_id']}", "Open game"))


async def tap_photo_game(user, chat_id, message_id, game_id) -> str:
    db = get_db()
    state = await db.bot_state.find_one({"_id": chat_id}) or {}
    pending = state.get("pending_photo")
    game = await db.games.find_one({"_id": object_id(game_id)})
    if not pending or not game:
        return "That one has expired. Send the photo again."
    await db.bot_state.update_one({"_id": chat_id}, {"$unset": {"pending_photo": ""}})
    await telegram.edit(chat_id, message_id, "Got it.")
    await add_match_photo(user, chat_id, game, pending["full"], pending["thumb"])
    return ""


# --- Button taps -------------------------------------------------------------

def object_id(value: str) -> ObjectId | None:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


async def on_tap(tap: dict) -> None:
    """A button was tapped. Its "data" says what to do, e.g. "r:i:<game id>"."""
    chat_id = tap["message"]["chat"]["id"]
    message_id = tap["message"]["message_id"]
    old_text = tap["message"].get("text", "")
    action, _, rest = tap.get("data", "").partition(":")

    user = await user_for(tap["from"]["id"])
    if not user:
        await telegram.answer_tap(tap["id"], "Connect Telegram in the Star Boy app first.")
        return

    try:
        if action == "r":  # RSVP: r:i:<game> = I'm in, r:o:<game> = can't make it
            toast = await tap_rsvp(user, chat_id, message_id, old_text, rest)
        elif action == "v":  # vote: v:c:<claim> = confirm, v:d:<claim> = dispute
            toast = await tap_vote(user, chat_id, message_id, old_text, rest)
        elif action == "g":  # picked which game a report is about
            toast = await tap_game(user, chat_id, message_id, rest)
        elif action == "ok":  # "Looks right ✅" under "Here's what I heard"
            toast = await tap_looks_right(user, chat_id, message_id, old_text, rest)
        elif action == "pg":  # picked which game a photo belongs to
            toast = await tap_photo_game(user, chat_id, message_id, rest)
        elif action == "ts":  # "Tap my stats 📋": start the button flow for a game
            toast = await tapflow.start(user, chat_id, message_id, object_id(rest))
        elif action == "t":  # a button inside that flow
            toast = await tapflow.on_tap(user, chat_id, message_id, rest)
        elif action == "vn":  # "Send a voice note 🎙️"
            toast = await tap_voice_note(user, chat_id, message_id, rest)
        elif action in ("rs", "rd"):  # the creator ticking who was on their side
            toast = await tapflow.on_side_tap(user, chat_id, message_id, action, rest)
        else:
            toast = ""
    except HTTPException as error:
        toast = str(error.detail)
    await telegram.answer_tap(tap["id"], toast[:190])


async def tap_rsvp(user, chat_id, message_id, old_text, rest) -> str:
    choice, _, game_id = rest.partition(":")
    game = await get_db().games.find_one({"_id": object_id(game_id)})
    if not game or game["status"] == "cancelled":
        return "This game is no longer on."
    status = "in" if choice == "i" else "out"
    await set_rsvp(game, user["_id"], status)
    answer = "You're in ✅ See you there!" if status == "in" else "You can't make it ❌ Next time!"
    # Rewrite the message so the answer stays visible; keep the buttons so they
    # can change it. Cut off an earlier answer first, or they would pile up.
    for earlier in ("\n\nYou're in ✅", "\n\nYou can't make it ❌"):
        old_text = old_text.split(earlier)[0]
    await telegram.edit(chat_id, message_id, f"{escape(old_text)}\n\n<b>{answer}</b>",
                        notify.rsvp_buttons(game["_id"]))
    return answer


async def tap_vote(user, chat_id, message_id, old_text, rest) -> str:
    choice, _, claim_id = rest.partition(":")
    db = get_db()
    claim = await db.claims.find_one({"_id": object_id(claim_id)})
    if not claim:
        return "That report was replaced by a newer one."
    if claim["status"] != "pending":
        await telegram.edit(chat_id, message_id, f"{escape(old_text)}\n\n<b>Already {claim['status']}.</b>")
        return f"Already {claim['status']}."
    game = await db.games.find_one({"_id": claim["game_id"]})
    invite = invite_of(game, user["_id"])
    if claim["user_id"] == user["_id"] or not invite or invite["status"] != "in":
        return "Only teammates who were in this game can confirm."

    await consensus.vote(claim["_id"], user["_id"], "confirm" if choice == "c" else "dispute")
    answer = "You confirmed ✅" if choice == "c" else "You disputed ❌"
    await telegram.edit(chat_id, message_id, f"{escape(old_text)}\n\n<b>{answer}</b>")
    return answer


async def tap_game(user, chat_id, message_id, game_id) -> str:
    db = get_db()
    game = await db.games.find_one({"_id": object_id(game_id)})
    if not game:
        return "I can't find that game."
    pitch = await notify.pitch_of(game)
    state = await db.bot_state.find_one({"_id": chat_id}) or {}
    pending = state.get("pending") or {}
    await notify.await_report(chat_id, game["_id"])  # also clears "pending"

    label = f"{pitch['name']} · {format_kickoff(game['kickoff_at'])}"
    if pending.get("file_id") or pending.get("text"):
        await telegram.edit(chat_id, message_id, f"About <b>{escape(label)}</b>.")
        await start_report_job(user, chat_id, game, pending.get("file_id"), pending.get("text"))
    else:
        await telegram.edit(chat_id, message_id,
                            f"How was your game at <b>{escape(label)}</b>? ⚽",
                            notify.report_buttons(game["_id"]))
    return ""


async def tap_voice_note(user, chat_id, message_id, game_id) -> str:
    game = await get_db().games.find_one({"_id": object_id(game_id)})
    if not game:
        return "I can't find that game."
    pitch = await notify.pitch_of(game)
    await notify.await_report(chat_id, game["_id"])
    await telegram.edit(chat_id, message_id,
                        f"<b>{escape(pitch['name'])}</b>\n"
                        "Send me a voice note now 🎙️ (or type it): your goals, your assists, "
                        "and anything else worth telling.")
    return ""


async def tap_looks_right(user, chat_id, message_id, old_text, job_id) -> str:
    db = get_db()
    job = await db.jobs.find_one({"_id": object_id(job_id), "input.user_id": user["_id"], "status": "done"})
    if not job or not job["result"].get("stats"):
        return "I can't find that report. Send it again."
    game = await db.games.find_one({"_id": job["input"]["game_id"]})
    report = job["result"]["stats"]
    await save_claim(game, user, job["result"]["transcript"], report,
                     [p["id"] for p in report["assisted_players"]],
                     source="voice" if job["input"].get("audio_path") else "text")
    # Done with this report (other things in the state, like a score being entered, stay).
    await db.bot_state.update_one(
        {"_id": chat_id}, {"$unset": {"awaiting_report_game_id": "", "pending": ""}})
    await telegram.edit(chat_id, message_id,
                        f"{escape(old_text)}\n\n<b>Submitted ✅ It counts once your teammates confirm.</b>",
                        notify.open_button(f"/game/{game['_id']}", "Open game"))
    return "Submitted ✅"


# --- Webhook mode (the deployed app) -------------------------------------------

async def register_webhook() -> None:
    """Tell Telegram to send updates to this server. Run at every start: it is
    harmless to repeat, and it means a fresh deploy needs no manual step."""
    if not settings.telegram_webhook_secret:
        log.error("TELEGRAM_WEBHOOK_SECRET is not set, so the bot can't receive messages.")
        return
    url = f"{settings.public_base_url}/api/telegram/webhook"
    ok = await telegram.call(
        "setWebhook", url=url, secret_token=settings.telegram_webhook_secret,
        allowed_updates=["message", "callback_query"],
    )
    if ok:
        log.info("Telegram webhook is set to %s", url)
    else:
        log.error("Telegram refused the webhook for %s", url)


# --- Polling mode (the laptop) -----------------------------------------------

async def poll_forever() -> None:
    """Ask Telegram for new updates again and again ("long polling")."""
    # If a webhook is set (the deployed app uses one), Telegram refuses polling,
    # and removing it would cut the live app off. So leave it alone.
    info = await telegram.call("getWebhookInfo")
    if info and info.get("url"):
        log.warning("The bot has a webhook set (the deployed app). Polling is OFF here, "
                    "so this local server won't receive Telegram messages.")
        return

    log.info("Telegram bot is polling for messages.")
    offset = 0
    while True:
        # timeout=30: Telegram keeps the call open up to 30 s and answers the
        # moment something arrives. So this loop is not busy, and replies are instant.
        updates = await telegram.call(
            "getUpdates", http_timeout=40,
            offset=offset, timeout=30, allowed_updates=["message", "callback_query"],
        )
        if updates is None:
            await asyncio.sleep(5)  # network trouble: wait a little, try again
            continue
        for update in updates:
            offset = update["update_id"] + 1
            # Don't wait for one player's update before reading the next.
            asyncio.create_task(handle_update(update))
