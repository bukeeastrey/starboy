"""Telegram: connect an account, receive updates (webhook), and the cron ping."""

import asyncio
import hmac
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from .. import bot, scheduler, telegram
from ..auth import current_user
from ..config import settings
from ..db import get_db
from ..util import now

router = APIRouter(prefix="/api")

LINK_VALID_FOR = timedelta(minutes=30)


@router.post("/telegram/link")
async def make_link(user: dict = Depends(current_user)):
    """A one-time link that opens the bot and connects it to this account."""
    username = await telegram.username() if telegram.enabled() else None
    if not username:
        raise HTTPException(503, "The Telegram bot isn't set up on this server yet.")
    token = secrets.token_urlsafe(16)
    await get_db().link_tokens.insert_one(
        {"_id": token, "user_id": user["_id"], "expires_at": now() + LINK_VALID_FOR}
    )
    # Opening this link starts the bot with "/start <token>" (see bot.on_start).
    return {"url": f"https://t.me/{username}?start={token}"}


@router.delete("/telegram/link")
async def disconnect(user: dict = Depends(current_user)):
    await get_db().users.update_one(
        {"_id": user["_id"]}, {"$set": {"telegram_chat_id": None, "telegram_username": None}}
    )
    return {"telegram_linked": False}


@router.post("/telegram/webhook", include_in_schema=False)
async def webhook(request: Request,
                  x_telegram_bot_api_secret_token: str = Header(default="")):
    """Telegram calls this for every message when the app is deployed."""
    secret = settings.telegram_webhook_secret
    # compare_digest: checking takes the same time whether it nearly matches or not.
    if not secret or not hmac.compare_digest(x_telegram_bot_api_secret_token, secret):
        raise HTTPException(403, "Forbidden.")
    update = await request.json()
    # Answer Telegram at once; do the work in the background.
    asyncio.create_task(bot.handle_update(update))
    return {"ok": True}


@router.get("/cron/tick")
async def cron_tick(token: str = ""):
    """Hit by a free cron service every 10 minutes: keeps the server awake
    and sends any reminders that are due."""
    if not settings.cron_token or not hmac.compare_digest(token, settings.cron_token):
        raise HTTPException(403, "Forbidden.")
    return await scheduler.tick()
