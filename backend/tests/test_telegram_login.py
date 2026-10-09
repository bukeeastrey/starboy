"""The Telegram Mini App sign-in check (Telegram's documented HMAC)."""

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from app.auth import telegram_user_from_init_data

TOKEN = "123456:TEST-TOKEN"


def make_init_data(user_id=42, auth_date=None, token=TOKEN, tamper=None) -> str:
    """Build launch data the way Telegram does, signed with `token`."""
    fields = {
        "auth_date": str(int(auth_date if auth_date is not None else time.time())),
        "query_id": "AAH-test",
        "user": json.dumps({"id": user_id, "first_name": "Tunde"}, separators=(",", ":")),
    }
    check_string = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if tamper:
        fields.update(tamper)
    return urlencode(fields)


def test_real_launch_data_is_accepted():
    user = telegram_user_from_init_data(make_init_data(user_id=42), TOKEN)
    assert user == {"id": 42, "first_name": "Tunde"}


def test_changing_the_user_breaks_the_signature():
    forged = make_init_data(tamper={"user": json.dumps({"id": 999, "first_name": "Tunde"})})
    assert telegram_user_from_init_data(forged, TOKEN) is None


def test_data_signed_with_another_bots_token_is_refused():
    assert telegram_user_from_init_data(make_init_data(token="999:OTHER"), TOKEN) is None


def test_old_or_future_data_is_refused():
    assert telegram_user_from_init_data(make_init_data(auth_date=time.time() - 3 * 86400), TOKEN) is None
    assert telegram_user_from_init_data(make_init_data(auth_date=time.time() + 3600), TOKEN) is None


def test_rubbish_is_refused():
    for rubbish in ("", "hash=abc", "not a query string", "user=%7B%7D&auth_date=1&hash="):
        assert telegram_user_from_init_data(rubbish, TOKEN) is None
    assert telegram_user_from_init_data(make_init_data(), "") is None  # no bot token configured


def test_web_app_buttons():
    from app import telegram
    markup = telegram.keyboard([[("Open", "webapp:https://x.example"), ("Link", "https://x.example"), ("Tap", "a:b")]])
    assert markup["inline_keyboard"][0] == [
        {"text": "Open", "web_app": {"url": "https://x.example"}},
        {"text": "Link", "url": "https://x.example"},
        {"text": "Tap", "callback_data": "a:b"},
    ]


def test_small_clock_differences_are_tolerated():
    assert telegram_user_from_init_data(make_init_data(auth_date=time.time() + 60), TOKEN) is not None


def test_the_sign_in_route(monkeypatch):
    """Through the real route: a linked player is signed in, others are not."""
    import random

    import pytest
    from fastapi.testclient import TestClient

    from app.config import settings
    from app.main import app

    if not settings.mongodb_uri:
        pytest.skip("MONGODB_URI is not set")
    monkeypatch.setattr(settings, "telegram_bot_token", TOKEN)
    telegram_id = random.randint(10**9, 10**10)
    with TestClient(app) as client:
        # Sign up on the web, then pretend the bot linked this Telegram account to it.
        phone = "0806" + "".join(random.choice("0123456789") for _ in range(7))
        client.post("/api/auth/signup", json={"name": "Mini App Tester", "phone": phone, "pin": "1234"}).raise_for_status()
        me = client.get("/api/me").json()

        async def link():
            from bson import ObjectId

            from app import db
            await db.get_db().users.update_one({"_id": ObjectId(me["id"])}, {"$set": {"telegram_chat_id": telegram_id}})
        client.portal.call(link)
        client.post("/api/auth/signout")
        client.cookies.clear()
        assert client.get("/api/me").status_code == 401

        ok = client.post("/api/auth/telegram", json={"init_data": make_init_data(user_id=telegram_id)})
        assert ok.status_code == 200 and ok.json()["name"] == "Mini App Tester"
        assert client.get("/api/me").json()["id"] == me["id"]          # the cookie is set

        client.cookies.clear()
        assert client.post("/api/auth/telegram", json={"init_data": make_init_data(user_id=1)}).status_code == 404
        assert client.post("/api/auth/telegram", json={"init_data": make_init_data(user_id=telegram_id, token="9:BAD")}).status_code == 401
