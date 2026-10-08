"""Point the Telegram bot at the deployed app (webhook mode), or back to the laptop.

From the backend folder:
    python scripts/set_webhook.py            use PUBLIC_BASE_URL from .env
    python scripts/set_webhook.py https://starboy.onrender.com
    python scripts/set_webhook.py --delete   remove the webhook (laptop polling works again)
    python scripts/set_webhook.py --info     show what is set now

Needs TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET (the same secret must be
set on the deployed app). Only one mode works at a time: with a webhook set,
the laptop no longer receives messages.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import telegram  # noqa: E402
from app.config import settings  # noqa: E402


async def main() -> None:
    if not settings.telegram_bot_token:
        sys.exit("TELEGRAM_BOT_TOKEN is not set in .env")
    argument = sys.argv[1] if len(sys.argv) > 1 else ""

    if argument == "--info":
        info = await telegram.call("getWebhookInfo") or {}
        print("Webhook:", info.get("url") or "(none: polling mode)")
        print("Waiting updates:", info.get("pending_update_count"))
        if info.get("last_error_message"):
            print("Last error:", info["last_error_message"])
        return

    if argument == "--delete":
        ok = await telegram.call("deleteWebhook")
        print("Webhook removed. The laptop can poll again." if ok else "Could not remove the webhook.")
        return

    base = (argument or settings.public_base_url).rstrip("/")
    if not base.startswith("https://"):
        sys.exit("Give the public https address, e.g. https://starboy.onrender.com")
    if not settings.telegram_webhook_secret:
        sys.exit("TELEGRAM_WEBHOOK_SECRET is not set in .env")

    ok = await telegram.call(
        "setWebhook",
        url=f"{base}/api/telegram/webhook",
        secret_token=settings.telegram_webhook_secret,
        allowed_updates=["message", "callback_query"],
    )
    print(f"Webhook set to {base}/api/telegram/webhook" if ok else "Telegram refused the webhook.")


if __name__ == "__main__":
    asyncio.run(main())
