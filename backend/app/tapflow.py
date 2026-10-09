"""The Telegram "Tap my stats 📋" flow: a report made with buttons, one
question at a time, for players who don't want to send a voice note.

  Goals? -> Assists? -> Defending? (keepers: Saves? + Clean sheet?)
        -> Man of the match? -> summary card -> Submit ✅

The answers are kept in `bot_state` (one document per chat) until the player
taps Submit. Then they become a normal claim, confirmed by teammates like
any other report. Also here: the game creator entering the final score."""

import re
from html import escape

from bson import ObjectId

from . import notify, results, summary, telegram
from .db import get_db
from .routes.games import game_phase, invite_of
from .routes.reports import save_claim
from .util import display_name, now, stat_line

# What each question stores, in order. Keepers get different questions.
OUTFIELD_STEPS = ["goals", "assists", "defending", "motm"]
KEEPER_STEPS = ["goals", "assists", "saves", "clean_sheet", "motm"]

QUESTIONS = {
    "goals": "Goals?",
    "assists": "Assists?",
    "saves": "Saves?",
    "clean_sheet": "Clean sheet? (dem no score you)",
    "defending": "Defending: blocks + tackles?",
    "motm": "Man of the match?",
}
COUNT_BUTTONS = ["0", "1", "2", "3", "4+"]  # "4+" asks for the exact number
MAX_COUNT = 20


def steps_for(user: dict) -> list[str]:
    return KEEPER_STEPS if user.get("position") == "GK" else OUTFIELD_STEPS


# --- The state kept between taps ---------------------------------------------

async def load_tap(chat_id: int) -> dict | None:
    state = await get_db().bot_state.find_one({"_id": chat_id, "expires_at": {"$gt": now()}})
    return (state or {}).get("tap")


async def save_tap(chat_id: int, tap: dict | None) -> None:
    change = ({"$set": {"tap": tap, "expires_at": now() + notify.AWAITING_REPORT_FOR}} if tap
              else {"$unset": {"tap": ""}})
    await get_db().bot_state.update_one({"_id": chat_id}, change, upsert=bool(tap))


async def other_players(game: dict, user: dict) -> list[dict]:
    """The other players who were in: the Man of the Match candidates."""
    ids = [uid for uid in notify.ids_with_status(game, "in") if uid != user["_id"]]
    users = await get_db().users.find({"_id": {"$in": ids}}).to_list(None)
    return sorted(users, key=lambda u: u["name"])


# --- Showing a step ----------------------------------------------------------

def summary_line(answers: dict, motm_name: str | None) -> str:
    """'2 goals · 1 assist · 3–5 blocks/tackles · MOTM vote: Emeka'"""
    line = stat_line({
        "goals": answers.get("goals"), "assists": answers.get("assists"),
        "saves": answers.get("saves"), "clean_sheet": answers.get("clean_sheet"),
        "defending": answers.get("defending"),
    })
    return f"{line} · MOTM vote: {motm_name}" if motm_name else line


async def show(chat_id: int, user: dict, tap: dict, message_id: int | None) -> None:
    """Show the next unanswered question, or the summary card when all are
    answered. Edits the same message when it can, so the chat stays tidy."""
    game = await get_db().games.find_one({"_id": tap["game_id"]})
    pitch = await notify.pitch_of(game)
    answers = tap["answers"]
    step = next((s for s in steps_for(user) if s not in answers), None)
    header = f"<b>{escape(pitch['name'])}</b>\n"

    if step is None:
        motm = await get_db().users.find_one({"_id": answers["motm"]}) if answers.get("motm") else None
        text = (header + escape(summary_line(answers, motm and display_name(motm)))
                + "\n\nNa so e be?")
        buttons = [[("Submit ✅", "t:ok"), ("Start again ↩️", "t:re")]]
    elif step == "motm":
        others = await other_players(game, user)
        text = header + QUESTIONS[step]
        names = [(display_name(u)[:20], f"t:m:{u['_id']}") for u in others[:12]]
        buttons = [names[i:i + 2] for i in range(0, len(names), 2)] + [[("Skip", "t:m:skip")]]
    elif step == "defending":
        text = header + QUESTIONS[step]
        buttons = [[(bucket.replace("-", "–"), f"t:d:{index}")
                    for index, bucket in enumerate(results.DEFENDING_BUCKETS)]]
    elif step == "clean_sheet":
        text = header + QUESTIONS[step]
        buttons = [[("Yes 🧤", "t:c:y"), ("No", "t:c:n")]]
    else:  # goals, assists, saves: a count
        text = header + QUESTIONS[step]
        buttons = [[(label, f"t:n:{step}:{label}") for label in COUNT_BUTTONS]]

    if message_id:
        await telegram.edit(chat_id, message_id, text, buttons)
    else:
        await telegram.send(chat_id, text, buttons)


# --- Taps --------------------------------------------------------------------

async def start(user: dict, chat_id: int, message_id: int | None, game_id) -> str:
    """"Tap my stats 📋" was tapped: begin with the first question."""
    game = await get_db().games.find_one({"_id": game_id})
    invite = game and invite_of(game, user["_id"])
    if (not game or game["status"] == "cancelled" or game_phase(game) == "upcoming"
            or not invite or invite["status"] != "in"):
        return "You can report a game after kickoff, once you're marked “in”."
    tap = {"game_id": game["_id"], "answers": {}, "awaiting_number": None}
    await save_tap(chat_id, tap)
    await show(chat_id, user, tap, message_id)
    return ""


async def on_tap(user: dict, chat_id: int, message_id: int, data: str) -> str:
    """A button inside the flow. `data` is what follows "t:", e.g. "n:goals:2"."""
    tap = await load_tap(chat_id)
    if not tap:
        return "That one has expired. Send /report to start again."
    answers = tap["answers"]
    kind, _, value = data.partition(":")

    if kind == "ok":
        return await submit(user, chat_id, message_id, tap)
    if kind == "re":
        tap = {"game_id": tap["game_id"], "answers": {}, "awaiting_number": None}
    elif kind == "n":  # a count: "goals:2" or "goals:4+"
        field, _, label = value.partition(":")
        if field not in ("goals", "assists", "saves"):
            return ""
        if label == "4+":
            # Ask for the exact number; the player types it (see on_number).
            tap["awaiting_number"] = field
            await save_tap(chat_id, tap)
            await telegram.edit(chat_id, message_id,
                                f"How many {field}? Type the number (4 or more).")
            return ""
        answers[field] = int(label)
    elif kind == "d":
        answers["defending"] = results.DEFENDING_BUCKETS[int(value)]
    elif kind == "c":
        answers["clean_sheet"] = value == "y"
    elif kind == "m":
        answers["motm"] = None if value == "skip" else ObjectId(value)

    tap["awaiting_number"] = None
    await save_tap(chat_id, tap)
    await show(chat_id, user, tap, message_id)
    return ""


async def on_number(user: dict, chat_id: int, text: str) -> bool:
    """The player typed the exact number after tapping "4+".
    Returns False if this message isn't an answer to that question."""
    tap = await load_tap(chat_id)
    if not tap or not tap.get("awaiting_number"):
        return False
    if not text.isdigit() or not 0 <= int(text) <= MAX_COUNT:
        await telegram.send(chat_id, f"Just the number, please (0 to {MAX_COUNT}).")
        return True
    tap["answers"][tap["awaiting_number"]] = int(text)
    tap["awaiting_number"] = None
    await save_tap(chat_id, tap)
    await show(chat_id, user, tap, None)  # their message is in between: send a new one
    return True


async def submit(user: dict, chat_id: int, message_id: int, tap: dict) -> str:
    """Submit ✅: the answers become a normal pending claim."""
    answers = tap["answers"]
    game = await get_db().games.find_one({"_id": tap["game_id"]})
    stats = {key: answers.get(key) for key in ("goals", "assists", "saves", "clean_sheet", "defending")}
    motm_id = answers.get("motm")
    # save_claim raises a friendly HTTPException if, say, it was already confirmed.
    claim = await save_claim(game, user, "", stats, [],
                             motm_vote_id=str(motm_id) if motm_id else "", source="buttons")
    await save_tap(chat_id, None)
    voted = claim["stats"].get("motm_vote")
    line = summary_line(claim["stats"], voted and voted["name"].split()[0])
    await telegram.edit(chat_id, message_id,
                        f"{escape(line)}\n\n<b>Submitted ✅ It counts once your teammates confirm.</b>",
                        notify.open_button(f"/game/{game['_id']}", "Open game"))
    return "Submitted ✅"


# --- The final score, from the game's creator --------------------------------

SCORE_PATTERN = re.compile(r"^\s*(\d{1,2})\s*[-:–]\s*(\d{1,2})\s*$")


async def on_score_text(user: dict, chat_id: int, text: str) -> bool:
    """The creator replied "5-3" to "What was the final score?".
    Returns False if this message isn't that."""
    match = SCORE_PATTERN.match(text)
    if not match:
        return False
    db = get_db()
    state = await db.bot_state.find_one({"_id": chat_id, "expires_at": {"$gt": now()}})
    game_id = (state or {}).get("awaiting_score_game_id")
    game = game_id and await db.games.find_one({"_id": game_id, "created_by": user["_id"]})
    if not game:
        return False

    score = {"game_id": game["_id"], "us": int(match.group(1)), "them": int(match.group(2)), "team": []}
    await db.bot_state.update_one({"_id": chat_id}, {"$set": {"score": score},
                                                     "$unset": {"awaiting_score_game_id": ""}})
    await show_sides(chat_id, user, score, None)
    return True


async def show_sides(chat_id: int, user: dict, score: dict, message_id: int | None) -> None:
    """"Who was on your side?": tap names to tick them, then Done."""
    game = await get_db().games.find_one({"_id": score["game_id"]})
    others = await other_players(game, user)
    text = (f"Final score: <b>{score['us']}–{score['them']}</b> (your side first).\n"
            "Who was on your side? Tap to tick, then Done.")
    names = [(("☑ " if u["_id"] in score["team"] else "☐ ") + display_name(u)[:18], f"rs:{u['_id']}")
             for u in others[:14]]
    buttons = [names[i:i + 2] for i in range(0, len(names), 2)] + [[("Done ✅", "rd")]]
    if message_id:
        await telegram.edit(chat_id, message_id, text, buttons)
    else:
        await telegram.send(chat_id, text, buttons)


async def on_side_tap(user: dict, chat_id: int, message_id: int, action: str, value: str) -> str:
    db = get_db()
    state = await db.bot_state.find_one({"_id": chat_id}) or {}
    score = state.get("score")
    if not score:
        return "That one has expired. Enter the score on the game page."

    if action == "rs":  # tick or untick one player
        player = ObjectId(value)
        team = [uid for uid in score["team"] if uid != player]
        if len(team) == len(score["team"]):
            team.append(player)
        score["team"] = team
        await db.bot_state.update_one({"_id": chat_id}, {"$set": {"score": score}})
        await show_sides(chat_id, user, score, message_id)
        return ""

    # Done ✅
    game = await db.games.find_one({"_id": score["game_id"], "created_by": user["_id"]})
    if not game:
        return "I can't find that game."
    await results.set_result(game, score["us"], score["them"], score["team"])
    await summary.maybe_queue(game["_id"])
    await db.bot_state.update_one({"_id": chat_id}, {"$unset": {"score": ""}})
    await telegram.edit(chat_id, message_id,
                        f"Final score saved: <b>{score['us']}–{score['them']}</b> ✅",
                        notify.open_button(f"/game/{game['_id']}", "Open game"))
    return "Saved ✅"
