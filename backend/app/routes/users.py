"""Sign up, sign in, sign out and "who am I?"."""

import re
import time

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from pymongo.errors import DuplicateKeyError

from .. import telegram
from ..auth import (clear_session_cookie, current_user, hash_pin, normalise_phone,
                    set_session_cookie, telegram_user_from_init_data, verify_pin)
from ..config import settings
from ..db import get_db
from ..util import now, public_user

router = APIRouter(prefix="/api")

POSITIONS = ["GK", "DEF", "MID", "FWD", "Anywhere"]

# A 4-digit PIN is easy to guess, so allow only a few wrong tries per phone.
MAX_WRONG_PINS = 5
LOCK_SECONDS = 10 * 60
_wrong_pins: dict[str, list[float]] = {}  # phone -> times of recent wrong tries


class SignUp(BaseModel):
    name: str
    nickname: str = ""
    phone: str
    position: str = "Anywhere"
    pin: str


class SignIn(BaseModel):
    phone: str
    pin: str


def me_view(user: dict) -> dict:
    """What a user sees about themselves (the only place a phone is returned)."""
    return {
        **public_user(user),
        "phone": user.get("phone", ""),
        # For the "Connect Telegram 🔔" card on the Home screen.
        "telegram_available": telegram.enabled(),
        "telegram_linked": bool(user.get("telegram_chat_id")),
    }


@router.post("/auth/signup")
async def signup(body: SignUp, response: Response):
    name = body.name.strip()
    if len(name) < 2:
        raise HTTPException(400, "Tell us your name.")
    if body.position not in POSITIONS:
        raise HTTPException(400, "Pick a position.")
    if not re.fullmatch(r"\d{4}", body.pin):
        raise HTTPException(400, "Your PIN must be exactly 4 digits.")

    user = {
        "name": name[:60],
        "nickname": body.nickname.strip()[:30],
        "phone": normalise_phone(body.phone),
        "position": body.position,
        "pin_hash": hash_pin(body.pin),
        "created_at": now(),
    }
    try:
        result = await get_db().users.insert_one(user)
    except DuplicateKeyError:
        # The unique index on "phone" stops two accounts with one number.
        raise HTTPException(409, "That phone number already has an account. Sign in instead.")

    set_session_cookie(response, result.inserted_id)
    return me_view(user)


@router.post("/auth/signin")
async def signin(body: SignIn, response: Response):
    phone = normalise_phone(body.phone)

    recent = [t for t in _wrong_pins.get(phone, []) if time.time() - t < LOCK_SECONDS]
    if len(recent) >= MAX_WRONG_PINS:
        raise HTTPException(429, "Too many wrong tries. Wait 10 minutes and try again.")

    user = await get_db().users.find_one({"phone": phone})
    # An account made in Telegram has no PIN: it signs in from the bot instead.
    if not user or not user.get("pin_hash") or not verify_pin(body.pin, user["pin_hash"]):
        _wrong_pins[phone] = recent + [time.time()]
        raise HTTPException(401, "Wrong phone number or PIN.")

    _wrong_pins.pop(phone, None)
    set_session_cookie(response, user["_id"])
    return me_view(user)


@router.get("/auth/magic")
async def magic_login(token: str = ""):
    """The one-time link the Telegram bot sends ("🌐 Open Star Boy"): signs
    the player in without a PIN and sends them to the app. It works once,
    and only for 10 minutes."""
    link = await get_db().login_tokens.find_one_and_delete(
        {"_id": token, "expires_at": {"$gt": now()}})
    response = RedirectResponse("/" if link else "/signin", status_code=303)
    if link:
        set_session_cookie(response, link["user_id"])
    return response


class TelegramSignIn(BaseModel):
    init_data: str


@router.post("/auth/telegram")
async def telegram_signin(body: TelegramSignIn, response: Response):
    """Sign in from the Telegram Mini App. The page sends the launch data
    Telegram gave it; if the check passes, we know who is holding the phone."""
    telegram_user = telegram_user_from_init_data(body.init_data, settings.telegram_bot_token)
    if not telegram_user:
        raise HTTPException(401, "That didn't come from Telegram.")
    # In a private chat, the chat's id is the person's Telegram id.
    user = await get_db().users.find_one({"telegram_chat_id": telegram_user["id"]})
    if not user:
        raise HTTPException(404, "Send /start to the Star Boy bot first, then open this again.")
    set_session_cookie(response, user["_id"])
    return me_view(user)


@router.post("/auth/signout")
async def signout(response: Response):
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/me")
async def me(user: dict = Depends(current_user)):
    return me_view(user)
