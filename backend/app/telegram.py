"""A small client for the Telegram Bot API (plain HTTPS calls with httpx)."""

import asyncio
import logging
from pathlib import Path

import httpx

from .config import settings

log = logging.getLogger("starboy.telegram")

API = "https://api.telegram.org"

# Telegram allows about 30 messages a second; stay well under it.
SEND_GAP_SECONDS = 0.05

_username: str | None = None  # the bot's @name, asked once and remembered


def enabled() -> bool:
    return settings.bot_mode != "off"


def public_url(path: str) -> str | None:
    """A link into the web app, or None on the laptop: Telegram refuses
    buttons that point to "localhost"."""
    base = settings.public_base_url.rstrip("/")
    return f"{base}{path}" if base.startswith("https://") else None


async def call(method: str, http_timeout: float = 20, **params) -> dict | list | bool | None:
    """Call one Bot API method. Returns its "result", or None if it failed.

    The token is part of the address, so errors are logged WITHOUT the address."""
    if not settings.telegram_bot_token:
        return None
    url = f"{API}/bot{settings.telegram_bot_token}/{method}"
    try:
        async with httpx.AsyncClient(timeout=http_timeout) as client:
            data = (await client.post(url, json=params)).json()
    except Exception as error:
        log.warning("Telegram %s failed: %s", method, type(error).__name__)
        return None
    if not data.get("ok"):
        log.warning("Telegram %s refused: %s", method, data.get("description"))
        return None
    return data["result"]


def keyboard(rows: list[list[tuple[str, str]]]) -> dict:
    """Buttons under a message. Each button is (label, action): an action
    starting with "https://" opens a link, anything else comes back to the
    bot as a tap ("callback")."""
    return {"inline_keyboard": [
        [
            {"text": label, "url": action} if action.startswith("https://")
            else {"text": label, "callback_data": action}
            for label, action in row
        ]
        for row in rows if row
    ]}


async def send(chat_id: int, text: str, buttons: list[list[tuple[str, str]]] | None = None) -> dict | None:
    """Send a message (HTML formatting), with optional buttons."""
    params = {"chat_id": chat_id, "text": text, "parse_mode": "HTML",
              "disable_web_page_preview": True}
    if buttons:
        params["reply_markup"] = keyboard(buttons)
    return await call("sendMessage", **params)


async def send_many(chat_ids: list[int], text: str, buttons=None) -> int:
    """The same message to several people, gently. Returns how many arrived."""
    sent = 0
    for chat_id in chat_ids:
        if await send(chat_id, text, buttons):
            sent += 1
        await asyncio.sleep(SEND_GAP_SECONDS)
    return sent


async def edit(chat_id: int, message_id: int, text: str, buttons=None) -> None:
    """Change a message the bot sent earlier (e.g. after a button tap)."""
    params = {"chat_id": chat_id, "message_id": message_id, "text": text,
              "parse_mode": "HTML", "disable_web_page_preview": True}
    if buttons:
        params["reply_markup"] = keyboard(buttons)
    await call("editMessageText", **params)


async def answer_tap(callback_id: str, text: str = "") -> None:
    """Stop the little spinner on a tapped button (optionally with a toast)."""
    await call("answerCallbackQuery", callback_query_id=callback_id, text=text)


async def download(file_id: str, destination: Path) -> bool:
    """Save a file someone sent the bot (a voice note) to disk."""
    info = await call("getFile", file_id=file_id)
    if not info or "file_path" not in info:
        return False
    url = f"{API}/file/bot{settings.telegram_bot_token}/{info['file_path']}"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(url)
            response.raise_for_status()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.content)
        return True
    except Exception as error:
        log.warning("Telegram file download failed: %s", type(error).__name__)
        return False


async def fetch(file_id: str) -> bytes | None:
    """The bytes of a file someone sent the bot (a photo), or None."""
    info = await call("getFile", file_id=file_id)
    if not info or "file_path" not in info:
        return None
    url = f"{API}/file/bot{settings.telegram_bot_token}/{info['file_path']}"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(url)
            response.raise_for_status()
        return response.content
    except Exception as error:
        log.warning("Telegram file download failed: %s", type(error).__name__)
        return None


async def username() -> str | None:
    """The bot's @username (without the @), for t.me links."""
    global _username
    if _username is None:
        me = await call("getMe")
        _username = me["username"] if me else None
    return _username
