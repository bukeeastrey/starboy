"""The bot's main menu, signing up inside Telegram, and the magic login link.

The main menu is a "reply keyboard": eight buttons that sit under the chat
box all the time. Tapping one sends its label as a normal message, which
`action_for()` turns back into an action."""

import secrets
from datetime import timedelta
from html import escape

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from . import flows, telegram
from .auth import normalise_phone
from .config import settings
from .db import get_db
from .util import display_name, now

MENU_ROWS = [
    ["⚽ New game", "📅 My games"],
    ["🏟 Pitches", "🏆 Leaderboards"],
    ["📋 Report a game", "⚖️ Settle it"],
    ["👤 My card", "🌐 Open Star Boy"],
]

# What each button (and each typed /command) does.
ACTIONS = {
    "⚽ New game": "newgame", "/newgame": "newgame",
    "📅 My games": "mygames", "/mygames": "mygames", "/next": "mygames",
    "🏟 Pitches": "pitches", "/pitches": "pitches",
    "🏆 Leaderboards": "leaderboards", "/leaderboard": "leaderboards", "/leaderboards": "leaderboards",
    "📋 Report a game": "report", "/report": "report",
    "⚖️ Settle it": "settle", "/settle": "settle",
    "👤 My card": "card", "/card": "card",
    "🌐 Open Star Boy": "open", "/open": "open",
    "/menu": "menu", "/help": "help",
}

POSITIONS = ["GK", "DEF", "MID", "FWD", "Anywhere"]
MAGIC_LINK_MINUTES = 10

HELP = (
    "<b>Star Boy</b> ⭐ gets you out of your room and onto the pitch.\n\n"
    "Use the buttons under the chat box:\n"
    "⚽ set up a game · 📅 your games\n"
    "🏟 pitches · 🏆 leaderboards\n"
    "📋 report a game · ⚖️ settle an argument\n"
    "👤 your player card · 🌐 the full app\n\n"
    "After a game, send me a <b>voice note</b> about how you played, "
    "or a <b>photo</b> for the match gallery."
)


def action_for(text: str) -> str | None:
    """The menu action a message asks for, or None if it's just text."""
    command = text.split()[0].split("@")[0] if text.startswith("/") else text
    return ACTIONS.get(command)


def keyboard() -> dict:
    return telegram.reply_keyboard(MENU_ROWS)


async def show(chat_id: int, text: str) -> None:
    """Send a message with the main menu under the chat box."""
    await telegram.send(chat_id, text, reply_markup=keyboard())


# --- "🌐 Open Star Boy": a one-time link that signs you in -----------------------

async def magic_link(user: dict, path: str = "/") -> str:
    """A link that opens the website already signed in. One use, 10 minutes."""
    token = secrets.token_urlsafe(24)
    await get_db().login_tokens.insert_one(
        {"_id": token, "user_id": user["_id"], "expires_at": now() + timedelta(minutes=MAGIC_LINK_MINUTES)})
    base = settings.public_base_url or "http://localhost:8000"
    return f"{base}/api/auth/magic?token={token}"


async def open_web(user: dict, chat_id: int) -> None:
    link = await magic_link(user)
    text = (f"Your door into Star Boy, {escape(display_name(user))}. "
            f"It opens once and closes in {MAGIC_LINK_MINUTES} minutes.")
    if link.startswith("https://"):
        # Inside Telegram (signed in automatically), or in the phone's browser (the one-time link).
        await telegram.send(chat_id, text, [[("⭐ Open inside Telegram", f"webapp:{settings.public_base_url}")],
                                            [("🌐 Open Star Boy", link)]])
    else:
        # Telegram refuses buttons that point at "localhost" (the laptop), so send it as text.
        await telegram.send(chat_id, f"{text}\n{link}")


# --- Signing up inside Telegram -------------------------------------------------

def telegram_name(sender: dict) -> str:
    """The name on their Telegram account, e.g. "Tunde Bello"."""
    return " ".join(part for part in [sender.get("first_name", ""), sender.get("last_name", "")] if part)[:60]


async def begin_signup(chat_id: int, sender: dict) -> None:
    flow = await flows.start(chat_id, "signup", "name", name=telegram_name(sender) or "Baller",
                             nickname="", position="Anywhere", username=sender.get("username"))
    await show_signup(chat_id, flow)


async def show_signup(chat_id: int, flow: dict, message_id: int | None = None) -> None:
    """Show the current sign-up question."""
    data, step = flow["data"], flow["step"]
    if step == "name":
        text = ("Welcome to <b>Star Boy</b> ⭐\nPickup football at your pitch: who's in, "
                "when's kickoff, and who really scored.\n\n"
                f"I'll put you down as <b>{escape(data['name'])}</b>.")
        buttons = [[("Use this ✅", "su:name:ok"), ("Change ✏️", "su:name:edit")], flows.nav("su", back=False)]
    elif step == "name_type":
        text = "No wahala. Type your name."
        buttons = [flows.nav("su")]
    elif step == "nickname":
        text = (f"Nice one, <b>{escape(data['name'])}</b>.\n\nWetin dem dey call you for pitch? "
                "Type your nickname, or skip.")
        buttons = [[("Skip", "su:nick:skip")], flows.nav("su")]
    elif step == "position":
        text = "Where do you like to play?"
        buttons = [[(p, f"su:pos:{p}") for p in POSITIONS[:4]], [("Anywhere", "su:pos:Anywhere")], flows.nav("su")]
    else:  # phone: Telegram's own "share my number" button lives on a reply keyboard
        await telegram.send(
            chat_id,
            "Last one. Share your number so friends who have it can find you here. "
            "It stays private: other players never see it. Or skip.",
            reply_markup=telegram.reply_keyboard(
                [[{"text": "Share my number 📱", "request_contact": True}], ["Skip"],
                 [flows.BACK, flows.CANCEL]], one_time=True))
        return

    if message_id:
        await telegram.edit(chat_id, message_id, text, buttons)
    else:
        await telegram.send(chat_id, text, buttons)


async def signup_tap(chat_id: int, message_id: int, data: str) -> str:
    """A button during sign-up. `data` is what follows "su:"."""
    flow = await flows.get(chat_id, "signup")
    if not flow:
        return flows.EXPIRED
    kind, _, value = data.partition(":")
    if kind == "back":
        flows.back(flow)
    elif kind == "name":
        flows.go(flow, "nickname" if value == "ok" else "name_type")
    elif kind == "nick":
        flow["data"]["nickname"] = ""
        flows.go(flow, "position")
    elif kind == "pos" and value in POSITIONS:
        flow["data"]["position"] = value
        flows.go(flow, "phone")
    await flows.save(chat_id, flow)
    if flow["step"] == "phone":
        await telegram.edit(chat_id, message_id, f"Position: <b>{flow['data']['position']}</b>")
        await show_signup(chat_id, flow)
    else:
        await show_signup(chat_id, flow, message_id)
    return ""


async def signup_message(chat_id: int, message: dict) -> bool:
    """A typed message (or a shared contact) during sign-up.
    Returns False if the chat isn't signing up."""
    flow = await flows.get(chat_id, "signup")
    if not flow:
        return False
    text = (message.get("text") or "").strip()
    step = flow["step"]

    if step == "name_type" and text:
        flow["data"]["name"] = text[:60]
        flows.go(flow, "nickname")
    elif step == "nickname" and text:
        flow["data"]["nickname"] = text[:30]
        flows.go(flow, "position")
    elif step == "phone":
        contact = message.get("contact")
        if text == flows.CANCEL:
            await cancel_signup(chat_id)
            return True
        if text == flows.BACK:
            flows.back(flow)
        elif contact:
            # Only their OWN number counts (the button guarantees it; a forwarded contact doesn't).
            if contact.get("user_id") != message["from"]["id"]:
                await telegram.send(chat_id, "Use the <b>Share my number 📱</b> button to share your own number.")
                return True
            await finish_signup(chat_id, flow, contact.get("phone_number", ""))
            return True
        elif text.lower() == "skip":
            await finish_signup(chat_id, flow, "")
            return True
        else:
            await telegram.send(chat_id, "Tap <b>Share my number 📱</b> or <b>Skip</b>.")
            return True
    else:
        # Typed something where a button was expected: show the question again.
        await show_signup(chat_id, flow)
        return True

    await flows.save(chat_id, flow)
    await show_signup(chat_id, flow)
    return True


async def cancel_signup(chat_id: int) -> None:
    await flows.clear(chat_id)
    await telegram.send(chat_id, "No wahala. Send /start whenever you're ready. ⚽",
                        reply_markup={"remove_keyboard": True})


async def finish_signup(chat_id: int, flow: dict, raw_phone: str) -> None:
    """Create the account (or connect the one that already has this number)."""
    db = get_db()
    data = flow["data"]
    phone = ""
    if raw_phone:
        try:
            phone = normalise_phone(raw_phone)
        except HTTPException:
            phone = ""  # an odd number: carry on without it

    link = {"telegram_chat_id": chat_id, "telegram_username": data.get("username"), "telegram_linked_at": now()}
    # One Telegram chat belongs to one account.
    await db.users.update_many({"telegram_chat_id": chat_id},
                               {"$set": {"telegram_chat_id": None, "telegram_username": None}})

    existing = phone and await db.users.find_one({"phone": phone})
    if existing:
        # They already joined on the website with this number: connect it, keep their profile.
        await db.users.update_one({"_id": existing["_id"]}, {"$set": link})
        await flows.clear(chat_id)
        await show(chat_id, f"Welcome back, <b>{escape(display_name(existing))}</b>! I found your "
                            "Star Boy account and connected it. The buttons below do everything. ⚽")
        return

    user = {"name": data["name"], "nickname": data["nickname"], "position": data["position"],
            "created_at": now(), "signed_up_in": "telegram", **link}
    if phone:
        user["phone"] = phone  # left out entirely when skipped (see the index in setup.py)
    try:
        await db.users.insert_one(user)
    except DuplicateKeyError:
        user.pop("phone", None)
        user.pop("_id", None)
        await db.users.insert_one(user)
    await flows.clear(chat_id)
    await show(chat_id, f"You're in, <b>{escape(display_name(user))}</b>! ⚽\n\n"
                        "Start with <b>🏟 Pitches</b> to find where your people play, "
                        "or <b>⚽ New game</b> to set one up. The buttons below do everything.")
