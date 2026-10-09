"""Games inside Telegram: the "⚽ New game" wizard and "📅 My games".

The wizard is a flow (see flows.py): pitch -> date -> time -> duration ->
note -> who to invite -> summary -> create. Every step has Back and Cancel.
Button taps arrive as "ng:<what>:<value>"; "mg:..." is My games."""

import calendar
import re
from datetime import date, datetime, timedelta, timezone
from html import escape
from urllib.parse import quote

from bson import ObjectId
from bson.errors import InvalidId

from . import flows, notify, pictures, telegram
from .config import settings
from .db import get_db
from .routes import games as game_routes
from .routes.pitches import register_at
from .util import WAT, display_name, format_kickoff, now

TIME_SLOTS = ["07:00", "08:00", "16:00", "17:00", "18:00", "19:00"]
DURATIONS = [60, 90, 120]
MAX_INVITE_BUTTONS = 40


def oid(value: str) -> ObjectId | None:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


def today() -> date:
    """Today's date in Lagos."""
    return now().astimezone(WAT).date()


def clock(time: str) -> str:
    """'17:00' -> '5pm', '07:30' -> '7:30am'."""
    hour, minute = int(time[:2]), time[3:]
    return f"{hour % 12 or 12}{'' if minute == '00' else ':' + minute}{'am' if hour < 12 else 'pm'}"


def parse_time(text: str) -> str | None:
    """'5pm', '5:30 pm', '17:30' -> 'HH:MM'. None if it isn't a clear time."""
    match = re.fullmatch(r"\s*(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm)?\s*", text.lower())
    if not match:
        return None
    hour, minute, half = int(match.group(1)), int(match.group(2) or 0), match.group(3)
    if minute > 59:
        return None
    if half:
        if not 1 <= hour <= 12:
            return None
        hour = hour % 12 + (12 if half == "pm" else 0)
    elif match.group(2) is None or hour > 23:
        return None  # "5" alone could be morning or evening: ask for am/pm
    return f"{hour:02d}:{minute:02d}"


def kickoff_of(data: dict) -> datetime:
    """The flow's Lagos date + time as a UTC datetime."""
    local = datetime.strptime(f"{data['date']} {data['time']}", "%Y-%m-%d %H:%M")
    return local.replace(tzinfo=WAT).astimezone(timezone.utc)


# --- ⚽ New game: showing each step ------------------------------------------

async def start(user: dict, chat_id: int, pitch_id: str | None = None) -> None:
    """Begin the wizard (optionally with the pitch already chosen)."""
    flow = await flows.start(chat_id, "ng", "pitch", invited=[])
    if pitch_id:
        flow["data"]["pitch_id"] = pitch_id
        flows.go(flow, "date")
        await flows.save(chat_id, flow)
    await show(user, chat_id, flow)


async def show(user: dict, chat_id: int, flow: dict, message_id: int | None = None) -> None:
    """Draw the wizard's current step, editing the same message when we can."""
    db = get_db()
    data, step = flow["data"], flow["step"]
    nav = flows.nav("ng", back=bool(flow["history"]))
    head = await header(data)

    if step == "pitch":
        registered = await db.registrations.distinct("pitch_id", {"user_id": user["_id"]})
        pitches = await db.pitches.find({"_id": {"$in": registered}}).sort("name", 1).to_list(20)
        text = "⚽ <b>New game</b>\nWhich pitch?" if pitches else (
            "⚽ <b>New game</b>\nYou haven't registered at a pitch yet. Pick one:")
        buttons = [[(p["name"][:40], f"ng:p:{p['_id']}")] for p in pitches] + [[("Other pitch…", "ng:other")], nav]
    elif step == "pitch_other":
        registered = await db.registrations.distinct("pitch_id", {"user_id": user["_id"]})
        others = await db.pitches.find({"_id": {"$nin": registered}}).sort("name", 1).to_list(12)
        text = ("Pick a pitch. I'll register you there too.\n"
                "Not listed? Cancel, then <b>🏟 Pitches</b> → Add a pitch.") if others else (
            "There are no other pitches yet. Cancel, then <b>🏟 Pitches</b> → Add a pitch.")
        buttons = [[(p["name"][:40], f"ng:p:{p['_id']}")] for p in others] + [nav]
    elif step == "date":
        day = today()
        saturday = day + timedelta(days=(5 - day.weekday()) % 7 or 7)
        sunday = day + timedelta(days=(6 - day.weekday()) % 7 or 7)
        text = head + "Which day?"
        buttons = [
            [("Today", f"ng:d:{day}"), ("Tomorrow", f"ng:d:{day + timedelta(days=1)}")],
            [(f"Sat {saturday.day} {saturday:%b}", f"ng:d:{saturday}"), (f"Sun {sunday.day} {sunday:%b}", f"ng:d:{sunday}")],
            [("📆 Pick a date", "ng:cal")], nav,
        ]
    elif step == "calendar":
        text = head + "Pick a date."
        buttons = month_grid(data.get("month") or f"{today():%Y-%m}") + [nav]
    elif step == "time":
        text = head + "Kickoff time?"
        slots = [(clock(t), f"ng:t:{t}") for t in TIME_SLOTS]
        buttons = [slots[:3], slots[3:], [("⌨️ Type a time", "ng:tt")], nav]
    elif step == "time_type":
        text = head + "Type the kickoff time, like <b>5pm</b>, <b>7:30am</b> or <b>17:30</b>."
        buttons = [nav]
    elif step == "duration":
        text = head + "How long?"
        buttons = [[(f"{m} min", f"ng:u:{m}") for m in DURATIONS], nav]
    elif step == "note":
        text = head + "Any note for the crew? Type it (e.g. “Bring white and dark shirts”), or skip."
        buttons = [[("Skip", "ng:ns")], nav]
    elif step == "invite":
        players = await invitable(data["pitch_id"], user)
        chosen = set(data["invited"])
        text = head + (f"Who are you inviting? Tap to tick. ({len(chosen)} of {len(players)})" if players else
                       "Nobody else has registered at this pitch yet. You can share the invite on WhatsApp after.")
        names = [(("✅ " if str(p["_id"]) in chosen else "⬜ ") + display_name(p)[:18], f"ng:i:{p['_id']}")
                 for p in players[:MAX_INVITE_BUTTONS]]
        buttons = [names[i:i + 2] for i in range(0, len(names), 2)]
        if players:
            buttons.append([("Select all", "ng:ia"), ("Done ➡️", "ng:id")])
        else:
            buttons.append([("Continue ➡️", "ng:id")])
        buttons.append(nav)
    else:  # summary
        in_past = kickoff_of(data) < now()
        text = head + (f"Inviting <b>{len(data['invited'])}</b> "
                       f"{'player' if len(data['invited']) == 1 else 'players'}.\n\n"
                       + ("This kickoff has already passed, so I'll save it as a game that was played.\n\n" if in_past else "")
                       + "All correct?")
        buttons = [[("Create ✅", "ng:ok"), ("Start over ↩️", "ng:re")], nav]

    if message_id:
        await telegram.edit(chat_id, message_id, text, buttons)
    else:
        await telegram.send(chat_id, text, buttons)


async def header(data: dict) -> str:
    """What has been chosen so far, shown at the top of every step."""
    lines = ["⚽ <b>New game</b>"]
    if data.get("pitch_id"):
        pitch = await get_db().pitches.find_one({"_id": oid(data["pitch_id"])})
        lines.append(f"🏟 {escape(pitch['name'])}")
    if data.get("date") and data.get("time"):
        lines.append(f"🗓 {format_kickoff(kickoff_of(data))}")
    elif data.get("date"):
        day = date.fromisoformat(data["date"])
        lines.append(f"🗓 {day:%a} {day.day} {day:%b}")
    if data.get("duration"):
        lines.append(f"⏱ {data['duration']} min")
    if data.get("note"):
        lines.append(f"📝 {escape(data['note'])}")
    return "\n".join(lines) + "\n\n"


def month_grid(month: str) -> list[list[tuple[str, str]]]:
    """An inline calendar for one month ("2026-10"). Days already gone are
    shown as a dot and do nothing."""
    year, number = int(month[:4]), int(month[5:7])
    first = date(year, number, 1)
    earliest, latest = today(), today() + timedelta(days=120)
    previous = (first - timedelta(days=1)).replace(day=1)
    following = (first + timedelta(days=32)).replace(day=1)

    rows = [[
        ("‹", f"ng:cm:{previous:%Y-%m}") if previous >= earliest.replace(day=1) else (" ", "ng:noop"),
        (f"{first:%B %Y}", "ng:noop"),
        ("›", f"ng:cm:{following:%Y-%m}") if following <= latest else (" ", "ng:noop"),
    ], [(day, "ng:noop") for day in ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")]]
    for week in calendar.Calendar().monthdayscalendar(year, number):
        row = []
        for day in week:
            if day == 0:
                row.append((" ", "ng:noop"))
            elif not earliest <= date(year, number, day) <= latest:
                row.append(("·", "ng:noop"))
            else:
                row.append((str(day), f"ng:d:{date(year, number, day)}"))
        rows.append(row)
    return rows


async def invitable(pitch_id: str, user: dict) -> list[dict]:
    """Everyone registered at the pitch except the player setting up the game."""
    db = get_db()
    ids = await db.registrations.distinct("user_id", {"pitch_id": oid(pitch_id), "user_id": {"$ne": user["_id"]}})
    return await db.users.find({"_id": {"$in": ids}}).sort("name", 1).to_list(200)


# --- ⚽ New game: taps and typed answers ---------------------------------------

async def on_tap(user: dict, chat_id: int, message_id: int, data: str) -> str:
    """A button in the wizard. `data` is what follows "ng:"."""
    flow = await flows.get(chat_id, "ng")
    if not flow:
        await telegram.edit(chat_id, message_id, flows.EXPIRED)
        return ""
    info = flow["data"]
    kind, _, value = data.partition(":")

    if kind == "noop":
        return ""
    if kind == "back":
        flows.back(flow)
    elif kind == "re":
        flow = await flows.start(chat_id, "ng", "pitch", invited=[])
    elif kind == "other":
        flows.go(flow, "pitch_other")
    elif kind == "p":
        pitch = await get_db().pitches.find_one({"_id": oid(value)})
        if not pitch:
            return "I can't find that pitch."
        await register_at(pitch["_id"], user["_id"])  # picking a pitch puts you on its list
        info["pitch_id"], info["invited"] = value, []
        flows.go(flow, "date")
    elif kind == "cal":
        flows.go(flow, "calendar")
    elif kind == "cm":
        info["month"] = value
    elif kind == "d":
        info["date"] = value
        flows.go(flow, "time")
    elif kind == "t":
        info["time"] = value
        flows.go(flow, "duration")
    elif kind == "tt":
        flows.go(flow, "time_type")
    elif kind == "u" and value.isdigit():
        info["duration"] = int(value)
        flows.go(flow, "note")
    elif kind == "ns":
        info["note"] = ""
        flows.go(flow, "invite")
    elif kind == "i":
        info["invited"] = ([v for v in info["invited"] if v != value] if value in info["invited"]
                           else info["invited"] + [value])
    elif kind == "ia":
        everyone = [str(p["_id"]) for p in await invitable(info["pitch_id"], user)]
        info["invited"] = [] if set(info["invited"]) == set(everyone) else everyone
    elif kind == "id":
        flows.go(flow, "summary")
    elif kind == "ok":
        return await create(user, chat_id, message_id, flow)

    await flows.save(chat_id, flow)
    await show(user, chat_id, flow, message_id)
    return ""


async def on_text(user: dict, chat_id: int, flow: dict, text: str) -> bool:
    """Something typed during the wizard: a time, or the note."""
    step = flow["step"]
    if step == "time_type":
        time = parse_time(text)
        if not time:
            await telegram.send(chat_id, "I didn't get that time. Try <b>5pm</b>, <b>7:30am</b> or <b>17:30</b>.",
                                [flows.nav("ng")])
            return True
        flow["data"]["time"] = time
        flows.go(flow, "duration")
    elif step == "note":
        flow["data"]["note"] = text[:200]
        flows.go(flow, "invite")
    else:
        # Typed where a button was expected: show the step again rather than guess.
        await telegram.send(chat_id, "Use the buttons for this one. 👇")
    await flows.save(chat_id, flow)
    await show(user, chat_id, flow)
    return True


async def create(user: dict, chat_id: int, message_id: int, flow: dict) -> str:
    """Create ✅: make the game, send invites, then the share link and poster."""
    db = get_db()
    data = flow["data"]
    pitch = await db.pitches.find_one({"_id": oid(data["pitch_id"])})
    game = await game_routes.make_game(pitch, user, kickoff_of(data), data["duration"], data.get("note", ""),
                                       [oid(v) for v in data["invited"]])
    await flows.clear(chat_id)

    when = format_kickoff(game["kickoff_at"])
    invited = len(game["invites"]) - 1
    link = telegram.public_url(f"/game/{game['_id']}")
    share = "\n".join(line for line in [
        f"⚽ Football at {pitch['name']}", f"🗓 {when}",
        f"📝 {game['note']}" if game["note"] else "", "", "You dey come? Tap to answer:", link or ""] if line or link)
    buttons = [[("📲 Share in the WhatsApp group", f"https://wa.me/?text={quote(share)}")]]
    if link:
        buttons.append([("Open game", link)])
    buttons.append([("📅 Manage this game", f"mg:{game['_id']}")])
    await telegram.edit(
        chat_id, message_id,
        f"✅ <b>Game set!</b>\n🏟 {escape(pitch['name'])}\n🗓 {when}\n\n"
        + (f"Invites sent to {invited} {'player' if invited == 1 else 'players'}. " if invited else "")
        + "Now tell the crew.", buttons)

    # The matchday poster, drawn here on the server, for WhatsApp Status.
    names = [display_name(user)]
    image = pictures.poster(pitch["name"], when, names, game["note"],
                            settings.public_base_url.replace("https://", ""))
    await telegram.send_photo(chat_id, image, "Your matchday poster. Post it on your Status. 📣")
    return "Game set ✅"


# --- 📅 My games ---------------------------------------------------------------

async def my_games(user: dict, chat_id: int, message_id: int | None = None) -> None:
    """Upcoming and recent games as buttons."""
    db = get_db()
    upcoming = await db.games.find(
        {"status": "scheduled", "kickoff_at": {"$gte": now() - timedelta(hours=3)},
         "invites": {"$elemMatch": {"user_id": user["_id"], "status": {"$in": ["in", "invited"]}}}}
    ).sort("kickoff_at", 1).to_list(6)
    upcoming = [g for g in upcoming if game_routes.game_phase(g) != "finished"]
    recent = await db.games.find(
        {"kickoff_at": {"$lte": now()}, "_id": {"$nin": [g["_id"] for g in upcoming]},
         "invites": {"$elemMatch": {"user_id": user["_id"], "status": "in"}}}
    ).sort("kickoff_at", -1).to_list(5)

    async def button(game: dict, mark: str) -> list[tuple[str, str]]:
        pitch = await notify.pitch_of(game)
        return [(f"{mark} {format_kickoff(game['kickoff_at'])} · {pitch['name']}"[:60], f"mg:{game['_id']}")]

    def mark_for(game: dict) -> str:
        if game["status"] == "cancelled":
            return "✖️"
        mine = game_routes.invite_of(game, user["_id"])
        return "✅" if mine and mine["status"] == "in" else "❓"

    buttons = [await button(g, mark_for(g)) for g in upcoming]
    buttons += [await button(g, "✖️" if g["status"] == "cancelled" else "🏁") for g in recent]
    if not buttons:
        text = "📅 <b>My games</b>\nNothing here yet. Na you go start am?"
    else:
        text = ("📅 <b>My games</b>\n✅ you're in · ❓ not answered · 🏁 played\nTap a game.")
    buttons.append([("⚽ New game", "ng:new")])
    if message_id:
        await telegram.edit(chat_id, message_id, text, buttons)
    else:
        await telegram.send(chat_id, text, buttons)


async def show_game(user: dict, chat_id: int, game_id, message_id: int | None = None, note: str = "") -> None:
    """One game: who's in, out and still to answer, and what you can do."""
    db = get_db()
    game = await db.games.find_one({"_id": game_id})
    if not game:
        await telegram.send(chat_id, "I can't find that game.")
        return
    pitch = await notify.pitch_of(game)
    users = {u["_id"]: u for u in await db.users.find(
        {"_id": {"$in": [i["user_id"] for i in game["invites"]]}}).to_list(None)}

    def names(status: str) -> str:
        found = [display_name(users[i["user_id"]]) for i in game["invites"]
                 if i["status"] == status and i["user_id"] in users]
        return f"({len(found)}) " + (escape(", ".join(found)) if found else "nobody")

    phase = game_routes.game_phase(game)
    cancelled = game["status"] == "cancelled"
    mine = game_routes.invite_of(game, user["_id"])
    my_status = mine["status"] if mine else None
    creator = game["created_by"] == user["_id"]
    gid = game["_id"]

    lines = [f"🏟 <b>{escape(pitch['name'])}</b>", f"🗓 {format_kickoff(game['kickoff_at'])} · {game['duration_min']} min"]
    if game.get("note"):
        lines.append(f"📝 {escape(game['note'])}")
    if cancelled:
        lines.append("\n✖️ <b>This game was cancelled.</b>")
    elif game.get("result"):
        lines.append(f"\n🏁 Final score: <b>{game['result']['us']}–{game['result']['them']}</b>")
    elif phase == "finished":
        lines.append("\n🏁 Full time. Score not in yet.")
    elif phase == "live":
        lines.append("\n🔥 Playing now.")
    lines += ["", f"✅ In {names('in')}", f"❌ Out {names('out')}", f"❓ No answer {names('invited')}"]
    if note:
        lines += ["", note]

    buttons = []
    if not cancelled and phase != "finished":
        buttons.append([("I'm in ✅" + (" ·" if my_status == "in" else ""), f"mg:in:{gid}"),
                        ("Can't make it ❌" + (" ·" if my_status == "out" else ""), f"mg:out:{gid}")])
        buttons.append([("➕ Invite more", f"mg:inv:{gid}")])
    if not cancelled and phase != "upcoming":
        if my_status == "in":
            buttons.append([("📋 Report my stats", f"mg:rep:{gid}"), ("📸 Add photos", f"mg:ph:{gid}")])
        if creator:
            buttons.append([("🏁 Enter final score + sides", f"mg:score:{gid}")])
    if creator and not cancelled and phase == "upcoming":
        buttons.append([("🗑 Cancel game", f"mg:can:{gid}")])
    link = telegram.public_url(f"/game/{gid}")
    if link:
        buttons.append([("Open game", link)])
    buttons.append([("⬅️ My games", "mg:list")])

    if message_id:
        await telegram.edit(chat_id, message_id, "\n".join(lines), buttons)
    else:
        await telegram.send(chat_id, "\n".join(lines), buttons)


async def on_my_games_tap(user: dict, chat_id: int, message_id: int, data: str) -> str:
    """A button under My games. `data` is what follows "mg:"."""
    db = get_db()
    action, _, value = data.partition(":")
    if action == "list":
        await my_games(user, chat_id, message_id)
        return ""
    if not value:  # "mg:<game id>": open that game
        await show_game(user, chat_id, oid(action), message_id)
        return ""

    game = await db.games.find_one({"_id": oid(value)})
    if not game:
        return "I can't find that game."
    pitch = await notify.pitch_of(game)
    creator = game["created_by"] == user["_id"]

    if action in ("in", "out"):
        if game["status"] == "cancelled":
            return "This game was cancelled."
        await game_routes.set_rsvp(game, user["_id"], action)
        await show_game(user, chat_id, game["_id"], message_id)
        return "You're in ✅" if action == "in" else "Can't make it ❌"

    if action == "inv":
        flow = await flows.start(chat_id, "inv", "pick", game_id=str(game["_id"]), invited=[])
        await show_invite_more(user, chat_id, flow, message_id)
    elif action == "can":
        if not creator:
            return "Only whoever set up the game can cancel it."
        await telegram.edit(chat_id, message_id,
                            f"Cancel the game at <b>{escape(pitch['name'])}</b>, "
                            f"{format_kickoff(game['kickoff_at'])}?\nEveryone who is in will be told.",
                            [[("Yes, cancel it 🗑", f"mg:cany:{game['_id']}")], [("No, keep it", f"mg:{game['_id']}")]])
    elif action == "cany":
        if not creator:
            return "Only whoever set up the game can cancel it."
        await game_routes.cancel(game, pitch)
        await show_game(user, chat_id, game["_id"], message_id)
        return "Game cancelled."
    elif action == "score":
        if not creator:
            return "Only whoever set up the game enters the score."
        await db.bot_state.update_one(
            {"_id": chat_id},
            {"$set": {"awaiting_score_game_id": game["_id"], "expires_at": now() + notify.AWAITING_REPORT_FOR}},
            upsert=True)
        await telegram.send(chat_id, f"What was the final score at <b>{escape(pitch['name'])}</b>?\n"
                                     "Reply like <b>5-3</b>, your side first. Then I'll ask who was on your side.",
                            [[(flows.CANCEL, "x")]])
    elif action == "rep":
        await notify.await_report(chat_id, game["_id"])
        await telegram.send(chat_id, notify.how_was_your_game(pitch), notify.report_buttons(game["_id"]))
    elif action == "ph":
        await db.bot_state.update_one(
            {"_id": chat_id},
            {"$set": {"photo_game_id": game["_id"], "expires_at": now() + notify.AWAITING_REPORT_FOR}}, upsert=True)
        await telegram.send(chat_id, f"📸 Send me your photos from <b>{escape(pitch['name'])}</b> now. "
                                     "They go straight into that game's gallery.", [[("Done", "done")]])
    return ""


# --- ➕ Invite more -------------------------------------------------------------

async def show_invite_more(user: dict, chat_id: int, flow: dict, message_id: int | None = None) -> None:
    db = get_db()
    game = await db.games.find_one({"_id": oid(flow["data"]["game_id"])})
    already = {invite["user_id"] for invite in game["invites"]}
    registered = await db.registrations.distinct("user_id", {"pitch_id": game["pitch_id"]})
    players = await db.users.find({"_id": {"$in": [u for u in registered if u not in already]}}).sort("name", 1).to_list(60)
    chosen = set(flow["data"]["invited"])

    if not players:
        text = ("Everyone registered at this pitch is already on the list. "
                "Share the game in your WhatsApp group to bring in more.")
        buttons = [[("⬅️ Back to the game", f"mg:{game['_id']}")]]
    else:
        text = f"➕ <b>Invite more</b>\nTap to tick. ({len(chosen)} chosen)"
        names = [(("✅ " if str(p["_id"]) in chosen else "⬜ ") + display_name(p)[:18], f"inv:i:{p['_id']}")
                 for p in players[:MAX_INVITE_BUTTONS]]
        buttons = [names[i:i + 2] for i in range(0, len(names), 2)]
        buttons += [[("Send invites ➡️", "inv:ok")], [(flows.BACK, f"mg:{game['_id']}"), (flows.CANCEL, "x")]]
    if message_id:
        await telegram.edit(chat_id, message_id, text, buttons)
    else:
        await telegram.send(chat_id, text, buttons)


async def on_invite_tap(user: dict, chat_id: int, message_id: int, data: str) -> str:
    flow = await flows.get(chat_id, "inv")
    if not flow:
        await telegram.edit(chat_id, message_id, flows.EXPIRED)
        return ""
    kind, _, value = data.partition(":")
    chosen = flow["data"]["invited"]
    if kind == "i":
        flow["data"]["invited"] = [v for v in chosen if v != value] if value in chosen else chosen + [value]
        await flows.save(chat_id, flow)
        await show_invite_more(user, chat_id, flow, message_id)
        return ""

    # Send invites ➡️
    db = get_db()
    game = await db.games.find_one({"_id": oid(flow["data"]["game_id"])})
    pitch = await notify.pitch_of(game)
    count = await game_routes.invite_more(game, pitch, user, [oid(v) for v in chosen])
    await flows.clear(chat_id)
    await show_game(user, chat_id, game["_id"], message_id,
                    note=f"📨 Invited {count} more {'player' if count == 1 else 'players'}." if count else "Nobody new to invite.")
    return "Invites sent ✅" if count else ""
