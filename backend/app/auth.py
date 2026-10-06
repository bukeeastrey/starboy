"""Sign-in helpers: PIN hashing, phone numbers and the session cookie."""

import hashlib
import hmac
import logging
import re
import secrets
from datetime import timedelta

from fastapi import HTTPException, Request, Response
from jose import JWTError, jwt

from .config import settings
from .db import get_db
from .util import now, oid

log = logging.getLogger("starboy.auth")

COOKIE_NAME = "starboy_session"
SESSION_DAYS = 30

# The key that signs session cookies (see SESSION_SECRET in .env.example).
_secret = settings.session_secret
if not _secret:
    _secret = secrets.token_hex(32)
    log.warning("SESSION_SECRET is not set: everyone is signed out at each restart.")


# --- PIN -----------------------------------------------------------------

def hash_pin(pin: str) -> str:
    """Hash a PIN with scrypt and a random salt. We never store the PIN itself."""
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(pin.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${key.hex()}"


def verify_pin(pin: str, stored: str) -> bool:
    try:
        _, salt_hex, key_hex = stored.split("$")
    except ValueError:
        return False
    key = hashlib.scrypt(pin.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
    # compare_digest takes the same time whether the PIN is nearly right or not.
    return hmac.compare_digest(key.hex(), key_hex)


# --- Phone ---------------------------------------------------------------

def normalise_phone(raw: str) -> str:
    """'0803 123 4567' and '+234 803 123 4567' both become '+2348031234567'."""
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits.startswith("0"):
        digits = "234" + digits[1:]
    if not 10 <= len(digits) <= 15:
        raise HTTPException(status_code=400, detail="That phone number doesn't look right.")
    return "+" + digits


# --- Session cookie ------------------------------------------------------

def set_session_cookie(response: Response, user_id) -> None:
    """Sign the user in: a signed token in a cookie that JavaScript can't read."""
    token = jwt.encode(
        {"sub": str(user_id), "exp": now() + timedelta(days=SESSION_DAYS)},
        _secret,
        algorithm="HS256",
    )
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_DAYS * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.public_base_url.startswith("https"),
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)


async def current_user(request: Request) -> dict:
    """FastAPI dependency: the signed-in user's document, or a 401 error."""
    token = request.cookies.get(COOKIE_NAME)
    if token:
        try:
            user_id = jwt.decode(token, _secret, algorithms=["HS256"])["sub"]
        except JWTError:
            user_id = None
        if user_id:
            user = await get_db().users.find_one({"_id": oid(user_id)})
            if user:
                return user
    raise HTTPException(status_code=401, detail="Please sign in.")
