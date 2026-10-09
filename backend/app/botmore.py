"""The rest of Star Boy inside Telegram: 🏟 Pitches, 🏆 Leaderboards,
⚖️ Settle it and 👤 My card.

Button taps arrive as "pi:…" (pitches), "lb:…" (leaderboards) and "st:…"
(settle it). Adding a pitch and Settle it are flows (see flows.py)."""

from html import escape
from urllib.parse import quote

from bson import ObjectId
from bson.errors import InvalidId

from . import flows, jobs, photos, pictures, settle, stats, telegram
from .config import FRONTEND_DIST, ROOT_DIR
from .db import get_db
from .routes import games as game_routes
from .routes.pitches import register_at
from .routes.players import player_profile
from .util import display_name, format_kickoff, now

# The boards, in the order they are offered: key, title, the stat, its column heading.
BOARDS = [
    ("golden_boot", "Golden Boot", "goals", "Goals"),
    ("playmaker", "Playmaker", "assists", "Assists"),
    ("most_consistent", "Most Consistent", "appearances", "Games"),
    ("most_wins", "Most Wins", "wins", "Wins"),
    ("most_motm", "Most MOTM", "motm", "MOTM"),
    ("the_wall", "The Wall", "wall", "Blocks"),
]
STOCK_COVERS = 5


def oid(value: str) -> ObjectId | None:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


async def my_pitches(user: dict) -> list[dict]:
    db = get_db()
    ids = await db.registrations.distinct("pitch_id", {"user_id": user["_id"]})
    return await db.pitches.find({"_id": {"$in": ids}}).sort("name", 1).to_list(30)


async def send_or_edit(chat_id: int, message_id: int | None, text: str, buttons) -> None:
    if message_id:
        await telegram.edit(chat_id, message_id, text, buttons)
    else:
        await telegram.send(chat_id, text, buttons)


# --- 🏟 Pitches ---------------------------------------------------------------

async def pitches(user: dict, chat_id: int, message_id: int | None = None) -> None:
    db = get_db()
    mine = set(await db.registrations.distinct("pitch_id", {"user_id": user["_id"]}))
    found = await db.pitches.find({"sport": "football"}).sort("name", 1).to_list(40)
    found.sort(key=lambda p: p["_id"] not in mine)  # yours first
    buttons = [[(("✓ " if p["_id"] in mine else "") + p["name"][:40], f"pi:{p['_id']}")] for p in found[:20]]
    buttons.append([("➕ Add a pitch", "pi:add")])
    await send_or_edit(chat_id, message_id, "🏟 <b>Pitches</b>\n✓ = you're registered there. Tap one.", buttons)


async def cover_image(pitch: dict) -> bytes | None:
    """The pitch's cover: the crew's own photo, or the same stock photo the website shows."""
    if pitch.get("cover_photo_id"):
        photo = await get_db().photos.find_one({"_id": pitch["cover_photo_id"]})
        if photo:
            return (await photos.read(photo, "full"))[0]
    number = sum(ord(ch) for ch in str(pitch["_id"])) % STOCK_COVERS + 1
    for folder in (FRONTEND_DIST / "img" / "covers", ROOT_DIR / "frontend" / "public" / "img" / "covers"):
        file = folder / f"cover-{number}.jpg"
        if file.is_file():
            return file.read_bytes()
    return None


async def show_pitch(user: dict, chat_id: int, pitch_id) -> None:
    """A pitch: its cover photo, the next game and the top three scorers."""
    db = get_db()
    pitch = await db.pitches.find_one({"_id": pitch_id})
    if not pitch:
        await telegram.send(chat_id, "I can't find that pitch.")
        return
    registered = bool(await db.registrations.find_one({"pitch_id": pitch["_id"], "user_id": user["_id"]}))
    players = await db.registrations.count_documents({"pitch_id": pitch["_id"]})
    upcoming = await db.games.find({"pitch_id": pitch["_id"], "status": "scheduled",
                                    "kickoff_at": {"$gte": now()}}).sort("kickoff_at", 1).to_list(1)
    boards = await stats.leaderboards(pitch["_id"], limit=3)

    lines = [f"🏟 <b>{escape(pitch['name'])}</b>"]
    if pitch.get("area"):
        lines.append(escape(pitch["area"]))
    lines.append(f"{players} {'player' if players == 1 else 'players'}" + (" · you're registered ✓" if registered else ""))
    if upcoming:
        in_count = sum(1 for i in upcoming[0]["invites"] if i["status"] == "in")
        lines += ["", f"⚽ Next game: <b>{format_kickoff(upcoming[0]['kickoff_at'])}</b> · {in_count} in"]
    else:
        lines += ["", "⚽ No game set yet."]
    if boards["golden_boot"]:
        lines += ["", "👟 <b>Golden Boot</b>"]
        lines += [f"{i}. {escape(row['nickname'] or row['name'])} ({row['goals']})"
                  for i, row in enumerate(boards["golden_boot"], start=1)]

    pid = pitch["_id"]
    buttons = []
    if not registered:
        buttons.append([("✅ Register here", f"pi:reg:{pid}")])
    buttons.append([("👥 Players", f"pi:pl:{pid}"), ("🏆 Leaderboards", f"lb:p:{pid}")])
    buttons.append([("⚽ New game here", f"ng:at:{pid}")])
    if upcoming:
        buttons.append([("Open the next game", f"mg:{upcoming[0]['_id']}")])
    if pitch.get("maps_url", "").startswith("https://"):
        buttons.append([("📍 Map", pitch["maps_url"])])
    link = telegram.public_url(f"/pitch/{pid}")
    if link:
        buttons.append([("Open on web", link)])
    buttons.append([("⬅️ All pitches", "pi:list")])

    image = await cover_image(pitch)
    if image:
        await telegram.send_photo(chat_id, image, "\n".join(lines), buttons)
    else:
        await telegram.send(chat_id, "\n".join(lines), buttons)


async def show_players(user: dict, chat_id: int, pitch_id) -> None:
    pitch = await get_db().pitches.find_one({"_id": pitch_id})
    players = sorted(await stats.pitch_players(pitch_id), key=lambda p: (-p["appearances"], p["name"]))
    rows = [f"{'Player':<16}{'Pos':<5}{'Gm':>3}{'Gl':>4}{'As':>4}"]
    rows += [f"{(p['nickname'] or p['name'])[:15]:<16}{p['position'][:3].upper():<5}"
             f"{p['appearances']:>3}{p['goals']:>4}{p['assists']:>4}" for p in players[:25]]
    text = (f"👥 <b>{escape(pitch['name'])}</b> · {len(players)} players\n"
            f"<pre>{escape(chr(10).join(rows))}</pre>\nGm games · Gl goals · As assists")
    await telegram.send(chat_id, text, [[("⬅️ Back to the pitch", f"pi:{pitch_id}")]])


async def on_pitch_tap(user: dict, chat_id: int, message_id: int | None, data: str) -> str:
    """A button about pitches. `data` is what follows "pi:"."""
    action, _, value = data.partition(":")
    if action == "list":
        await pitches(user, chat_id, message_id)
    elif action == "add":
        flow = await flows.start(chat_id, "ap", "name")
        await show_add_pitch(chat_id, flow, message_id)
    elif action in ("apskip", "back"):
        return await add_pitch_tap(user, chat_id, message_id, action)
    elif action == "reg":
        pitch = await get_db().pitches.find_one({"_id": oid(value)})
        if not pitch:
            return "I can't find that pitch."
        await register_at(pitch["_id"], user["_id"])
        await show_pitch(user, chat_id, pitch["_id"])
        return f"You're registered at {pitch['name']} ✅"
    elif action == "pl":
        await show_players(user, chat_id, oid(value))
    else:  # "pi:<pitch id>"
        await show_pitch(user, chat_id, oid(action))
    return ""


# --- ➕ Add a pitch (a flow: name -> area -> location) ---------------------------

async def show_add_pitch(chat_id: int, flow: dict, message_id: int | None = None) -> None:
    step, data = flow["step"], flow["data"]
    if step == "name":
        await send_or_edit(chat_id, message_id, "➕ <b>Add a pitch</b>\nWhat do people call it? Type the name.",
                           [flows.nav("pi", back=False)])
    elif step == "area":
        await send_or_edit(chat_id, message_id,
                           f"➕ <b>{escape(data['name'])}</b>\nWhere is it? Type the area or a landmark, or skip.",
                           [[("Skip", "pi:apskip")], flows.nav("pi")])
    else:  # location: Telegram's own "share location" button lives on a reply keyboard
        await telegram.send(
            chat_id,
            f"➕ <b>{escape(data['name'])}</b>\nAre you at the pitch now? Share your location so people can find it. Or skip.",
            reply_markup=telegram.reply_keyboard(
                [[{"text": "Share location 📍", "request_location": True}], ["Skip"], [flows.BACK, flows.CANCEL]],
                one_time=True))


async def add_pitch_tap(user: dict, chat_id: int, message_id: int | None, action: str) -> str:
    flow = await flows.get(chat_id, "ap")
    if not flow:
        await send_or_edit(chat_id, message_id, flows.EXPIRED, None)
        return ""
    if action == "back":
        flows.back(flow)
    else:  # skip the area
        flow["data"]["area"] = ""
        flows.go(flow, "location")
    await flows.save(chat_id, flow)
    await show_add_pitch(chat_id, flow, message_id if flow["step"] != "location" else None)
    return ""


async def add_pitch_message(user: dict, chat_id: int, flow: dict, message: dict) -> bool:
    """Something typed (or a shared location) while adding a pitch."""
    from . import botmenu  # here: botmenu doesn't need this file

    text = (message.get("text") or "").strip()
    step, data = flow["step"], flow["data"]
    if step == "name":
        if len(text) < 3:
            await telegram.send(chat_id, "Give it a name of at least 3 letters.")
            return True
        data["name"] = text[:80]
        flows.go(flow, "area")
    elif step == "area":
        data["area"] = text[:200]
        flows.go(flow, "location")
    else:  # location
        location = message.get("location")
        if text == flows.CANCEL:
            await flows.clear(chat_id)
            await botmenu.show(chat_id, "Cancelled. 👍")
            return True
        if text == flows.BACK:
            flows.back(flow)
        elif location or text.lower() == "skip":
            maps_url = f"https://maps.google.com/?q={location['latitude']},{location['longitude']}" if location else ""
            pitch = {"name": data["name"], "area": data.get("area", ""), "maps_url": maps_url, "sport": "football",
                     "created_by": user["_id"], "created_at": now()}
            await get_db().pitches.insert_one(pitch)
            await register_at(pitch["_id"], user["_id"])
            await flows.clear(chat_id)
            # Put the main menu back under the chat box, then show the new pitch.
            await botmenu.show(chat_id, f"✅ <b>{escape(pitch['name'])}</b> is on Star Boy, and you're registered there.")
            await show_pitch(user, chat_id, pitch["_id"])
            return True
        else:
            await telegram.send(chat_id, "Tap <b>Share location 📍</b> or <b>Skip</b>.")
            return True
    await flows.save(chat_id, flow)
    await show_add_pitch(chat_id, flow)
    return True


# --- 🏆 Leaderboards -----------------------------------------------------------

async def leaderboards(user: dict, chat_id: int, message_id: int | None = None) -> None:
    """Pick a pitch (skipped if you only have one), then a board."""
    mine = await my_pitches(user)
    if not mine:
        await send_or_edit(chat_id, message_id, "🏆 Register at a pitch first: tap <b>🏟 Pitches</b>.", None)
    elif len(mine) == 1:
        await show_board(chat_id, message_id, mine[0]["_id"], "golden_boot")
    else:
        await send_or_edit(chat_id, message_id, "🏆 <b>Leaderboards</b>\nWhich pitch?",
                           [[(p["name"][:40], f"lb:p:{p['_id']}")] for p in mine])


async def show_board(chat_id: int, message_id: int | None, pitch_id, board: str) -> None:
    """One leaderboard as a neat fixed-width table, top 10."""
    pitch = await get_db().pitches.find_one({"_id": pitch_id})
    key, title, stat, heading = next(b for b in BOARDS if b[0] == board)
    rows = (await stats.leaderboards(pitch_id))[key]

    if rows:
        table = [f"{'#':>2}  {'Player':<17}{heading:>7}"]
        table += [f"{i:>2}  {(row['nickname'] or row['name'])[:16]:<17}{round(row[stat]):>7}"
                  for i, row in enumerate(rows, start=1)]
        body = f"<pre>{escape(chr(10).join(table))}</pre>"
    else:
        body = "Nobody on this board yet. Play, report, confirm. ⚽"
    text = f"🏆 <b>{title}</b> · {escape(pitch['name'])}\n{body}\nConfirmed stats only."

    others = [(("• " if b[0] == board else "") + b[1], f"lb:b:{pitch_id}:{b[0]}") for b in BOARDS]
    buttons = [others[0:2], others[2:4], others[4:6]]
    link = telegram.public_url(f"/pitch/{pitch_id}")
    if rows:
        share = "\n".join([f"⭐ {pitch['name']} · {title}"]
                          + [f"{i}. {row['nickname'] or row['name']} ({round(row[stat])})" for i, row in enumerate(rows[:5], start=1)]
                          + ([link] if link else []))
        buttons.append([("📲 Share to WhatsApp", f"https://wa.me/?text={quote(share)}")])
    await send_or_edit(chat_id, message_id, text, buttons)


async def on_board_tap(user: dict, chat_id: int, message_id: int | None, data: str) -> str:
    """`data` is "p:<pitch>" (pitch chosen) or "b:<pitch>:<board>"."""
    kind, _, value = data.partition(":")
    if kind == "p":
        await show_board(chat_id, message_id, oid(value), "golden_boot")
    else:
        pitch_id, _, board = value.partition(":")
        if board in [b[0] for b in BOARDS]:
            await show_board(chat_id, message_id, oid(pitch_id), board)
    return ""


# --- ⚖️ Settle it (a flow: pitch -> player A -> player B -> scope) --------------

async def settle_start(user: dict, chat_id: int, message_id: int | None = None, player_a: str | None = None) -> None:
    mine = await my_pitches(user)
    if not mine:
        await send_or_edit(chat_id, message_id, "⚖️ Register at a pitch first: tap <b>🏟 Pitches</b>.", None)
        return
    flow = await flows.start(chat_id, "st", "pitch", a=player_a)
    if len(mine) == 1:
        flow["data"]["pitch_id"] = str(mine[0]["_id"])
        flow["step"] = "b" if player_a else "a"
        await flows.save(chat_id, flow)
    await show_settle(user, chat_id, flow, message_id)


async def show_settle(user: dict, chat_id: int, flow: dict, message_id: int | None = None) -> None:
    db = get_db()
    data, step = flow["data"], flow["step"]
    nav = flows.nav("st", back=bool(flow["history"]))
    head = "⚖️ <b>Settle it</b>\n"

    async def name_of(player_id: str) -> str:
        return escape(display_name(await db.users.find_one({"_id": oid(player_id)})))

    if step == "pitch":
        text = head + "Which pitch?"
        buttons = [[(p["name"][:40], f"st:p:{p['_id']}")] for p in await my_pitches(user)] + [nav]
    elif step in ("a", "b"):
        players = await stats.pitch_players(oid(data["pitch_id"]))
        players.sort(key=lambda p: (p["id"] != str(user["_id"]), p["name"]))  # you first
        taken = data.get("a") if step == "b" else None
        text = head + ("Who is Player A?" if step == "a" else f"<b>{await name_of(data['a'])}</b> versus who?")
        names = [((p["nickname"] or p["name"])[:20], f"st:{step}:{p['id']}") for p in players if p["id"] != taken][:40]
        buttons = [names[i:i + 2] for i in range(0, len(names), 2)] + [nav]
    else:  # scope
        text = head + f"<b>{await name_of(data['a'])}</b> vs <b>{await name_of(data['b'])}</b>\nBased on what?"
        past = await game_routes.past_games(oid(data["pitch_id"]), user, limit=6)
        played = [g for g in past["games"] if g["status"] != "cancelled"]
        buttons = [[("All time at this pitch", "st:s:all")]]
        buttons += [[(f"Only {g['kickoff_label']}", f"st:s:{g['id']}")] for g in played]
        buttons.append(nav)
    await send_or_edit(chat_id, message_id, text, buttons)


async def on_settle_tap(user: dict, chat_id: int, message_id: int | None, data: str) -> str:
    """A button in Settle it. `data` is what follows "st:"."""
    kind, _, value = data.partition(":")
    if kind == "new":  # "Settle it with…" under a player card: that player is A
        await settle_start(user, chat_id, None, player_a=value or None)
        return ""
    flow = await flows.get(chat_id, "st")
    if not flow:
        await send_or_edit(chat_id, message_id, flows.EXPIRED, None)
        return ""
    info = flow["data"]

    if kind == "back":
        flows.back(flow)
    elif kind == "p":
        info["pitch_id"] = value
        flows.go(flow, "b" if info.get("a") else "a")
    elif kind == "a":
        info["a"] = value
        flows.go(flow, "b")
    elif kind == "b":
        info["b"] = value
        flows.go(flow, "scope")
    elif kind == "s":
        return await settle_run(user, chat_id, message_id, flow, None if value == "all" else value)
    await flows.save(chat_id, flow)
    await show_settle(user, chat_id, flow, message_id)
    return ""


def versus_table(names: dict, table: list[dict]) -> str:
    """The comparison as fixed-width text: Tunde | stat | Bayo."""
    a, b = names["a"][:9], names["b"][:9]
    lines = [f"{a:>9}  {'':<17}{b:<9}"]
    lines += [f"{row['a']:>9}  {row['label'][:16]:<17}{row['b']:<9}" for row in table]
    return "\n".join(lines)


async def settle_run(user: dict, chat_id: int, message_id: int | None, flow: dict, game_id: str | None) -> str:
    """Scope chosen: show the table now; the verdict follows when Gemma is done."""
    db = get_db()
    info = flow["data"]
    user_a = await db.users.find_one({"_id": oid(info["a"])})
    user_b = await db.users.find_one({"_id": oid(info["b"])})
    pitch = await db.pitches.find_one({"_id": oid(info["pitch_id"])})
    game = await db.games.find_one({"_id": oid(game_id)}) if game_id else None
    await flows.clear(chat_id)

    result = await settle.begin(user_a, user_b, pitch, game, asked_by=user["_id"], telegram_chat_id=chat_id)
    title = f"⚖️ <b>{escape(display_name(user_a))} vs {escape(display_name(user_b))}</b>\n{escape(result['scope'])}"
    if not result["enough"]:
        await send_or_edit(chat_id, message_id, f"{title}\n\n{result['message']}", [[("⚖️ Try another pair", "st:new")]])
        return ""
    await send_or_edit(chat_id, message_id,
                       f"{title}\n<pre>{escape(versus_table(result['names'], result['table']))}</pre>\n"
                       "🤔 Star Boy is thinking it over…", None)
    return ""


@jobs.on_finished
async def send_verdict(job: dict) -> None:
    """The verdict job is done: send it to the chat that asked."""
    chat_id = (job.get("input") or {}).get("telegram_chat_id")
    if job["type"] != "verdict" or not chat_id:
        return
    data = job["input"]
    names = data["names"]
    if job["status"] != "done":
        await telegram.send(chat_id, "I couldn't write a verdict this time. The numbers above still stand.")
        return
    verdict = job["result"]["text"]
    winner = names.get(data["winner"])
    headline = f"🏆 <b>{escape(winner)}</b> takes it." if winner else "🤝 <b>It's a draw.</b>"
    share = "\n".join([f"⚖️ Settle it: {names['a']} vs {names['b']}", data.get("scope", ""), ""]
                      + [f"{row['label']}: {row['a']} / {row['b']}" for row in data["table"]] + ["", verdict])
    await telegram.send(chat_id, f"{headline}\n\n{escape(verdict)}",
                        [[("📲 Share to WhatsApp", f"https://wa.me/?text={quote(share[:1500])}")],
                         [("⚖️ Settle another", "st:new")]])


# --- 👤 My card -----------------------------------------------------------------

OUTFIELD = [("goals", "GLS"), ("assists", "AST"), ("wins", "WIN"), ("motm", "MOTM"), ("appearances", "APP"), ("wall", "DEF")]
KEEPER = [("saves", "SAV"), ("clean_sheets", "CS"), ("wins", "WIN"), ("motm", "MOTM"), ("appearances", "APP"), ("goals", "GLS")]


async def my_card(user: dict, chat_id: int) -> None:
    """Send the player card as a picture, drawn like the card on the website."""
    profile = await player_profile(str(user["_id"]), me=user)
    totals = profile["totals"]
    numbers = [(label, round(totals.get(key, 0))) for key, label in (KEEPER if user.get("position") == "GK" else OUTFIELD)]

    photo = None
    if user.get("avatar_photo_id"):
        stored = await get_db().photos.find_one({"_id": user["avatar_photo_id"]})
        if stored:
            photo = (await photos.read(stored, "full"))[0]

    image = pictures.player_card(
        user["name"], user.get("nickname", ""), user.get("position", "Anywhere"), str(user["_id"]),
        numbers, profile["form"], (profile["played_like"] or {}).get("name"), totals["appearances"], photo)

    badges = ", ".join(badge["name"] for badge in profile["badges"][:4])
    caption = f"👤 <b>{escape(user['name'])}</b>"
    if profile["streak"] > 1:
        caption += f"\n🔥 {profile['streak']} wins in a row"
    if badges:
        caption += f"\nPlayed like: {escape(badges)}"
    if not totals["appearances"]:
        caption += "\nNo confirmed games yet. Play one, report it, and this card fills up. ⚽"
    buttons = [[("⚖️ Settle it with…", f"st:new:{user['_id']}")]]
    link = telegram.public_url(f"/player/{user['_id']}")
    if link:
        buttons.append([("Open on web", link)])
    await telegram.send_photo(chat_id, image, caption, buttons)
