"""Conversation state for the Telegram bot's step-by-step flows.

A "flow" is a short conversation with buttons: signing up, setting up a game,
settling an argument. Where a player is in a flow is kept in MongoDB, one
document per chat, so two people using the bot at the same moment never mix,
and a server restart loses nothing.

Rules every flow follows:
- every step has Back and Cancel;
- a flow left alone for 30 minutes is closed, with a friendly message;
- tapping a main-menu button always leaves the current flow."""

from datetime import timedelta

from .db import get_db
from .util import now

FLOW_MINUTES = 30
EXPIRED = "⌛ That one sat for a while, so I closed it. Tap a menu button to start again."

BACK = "⬅️ Back"
CANCEL = "✖️ Cancel"


def nav(prefix: str, back: bool = True) -> list[tuple[str, str]]:
    """The last row of buttons on every step: Back and Cancel."""
    row = [(BACK, f"{prefix}:back")] if back else []
    return row + [(CANCEL, "x")]


async def get(chat_id: int, name: str | None = None) -> dict | None:
    """The chat's current flow, or None. If it has expired it is cleared, and
    None is returned with `was_expired(chat_id)` true once."""
    db = get_db()
    state = await db.bot_state.find_one({"_id": chat_id})
    flow = (state or {}).get("flow")
    if not flow:
        return None
    if flow["expires_at"] <= now():
        await db.bot_state.update_one({"_id": chat_id}, {"$unset": {"flow": ""},
                                                         "$set": {"flow_expired": True}})
        return None
    if name and flow["name"] != name:
        return None
    return flow


async def was_expired(chat_id: int) -> bool:
    """True once after a flow timed out, so the bot can say so one time."""
    state = await get_db().bot_state.find_one_and_update(
        {"_id": chat_id, "flow_expired": True}, {"$unset": {"flow_expired": ""}})
    return bool(state)


async def start(chat_id: int, flow_name: str, step: str, **data) -> dict:
    """Begin a flow (replacing any other one in this chat). Everything after
    the step is the flow's own data, e.g. start(chat, "signup", "name", name="Tunde")."""
    flow = {"name": flow_name, "step": step, "data": data, "history": []}
    await save(chat_id, flow)
    return flow


async def save(chat_id: int, flow: dict) -> None:
    """Store the flow and push its 30-minute deadline forward."""
    flow["expires_at"] = now() + timedelta(minutes=FLOW_MINUTES)
    await get_db().bot_state.update_one(
        {"_id": chat_id},
        # The chat's document must outlive the flow, so other state isn't lost.
        {"$set": {"flow": flow, "expires_at": now() + timedelta(days=2)},
         "$unset": {"flow_expired": ""}},
        upsert=True,
    )


def go(flow: dict, step: str) -> None:
    """Move to a step, remembering where we came from (for Back)."""
    flow["history"].append(flow["step"])
    flow["step"] = step


def back(flow: dict) -> bool:
    """Return to the previous step. False if this was the first one."""
    if not flow["history"]:
        return False
    flow["step"] = flow["history"].pop()
    return True


async def clear(chat_id: int) -> None:
    """Leave whatever the chat was in the middle of: a flow, a half-tapped
    report, a score being entered. Used by Cancel and by the main menu."""
    await get_db().bot_state.update_one(
        {"_id": chat_id},
        {"$unset": {"flow": "", "flow_expired": "", "tap": "", "score": "", "pending": "",
                    "pending_photo": "", "awaiting_score_game_id": "", "photo_game_id": ""}},
    )
