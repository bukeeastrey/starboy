"""Star Boy backend: the API, plus (once built) the React app itself."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from . import bot, db, jobs, llm, prompts, scheduler, setup
from . import pipeline, summary  # noqa: F401  (importing them registers their AI jobs)
from .config import AUDIO_DIR, FRONTEND_DIST, settings
from .routes import games, home, pitches, players, reports, settle, telegram, users

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
# httpx logs every address it calls, and Telegram addresses contain the bot
# token. Only let it log warnings, so the secret never reaches the log.
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("starboy")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once when the server starts, and once when it stops.
    db.connect()

    # A voice note left over from a crash must not stay on disk.
    if AUDIO_DIR.is_dir():
        for leftover in AUDIO_DIR.iterdir():
            leftover.unlink(missing_ok=True)

    try:
        await setup.ensure_indexes()
        await setup.seed_pitches()
    except Exception as error:
        # Keep the server up so /api/health can say what is wrong.
        log.error("Database setup failed: %s", type(error).__name__)

    await jobs.start()
    background = [
        # Load Gemma now, so the first voice note isn't the slow one.
        asyncio.create_task(llm.warm_up(prompts.EXTRACT_SYSTEM)),
        # Reminders: checked every minute.
        asyncio.create_task(scheduler.run_forever()),
    ]
    if settings.bot_mode == "polling":
        # On the laptop the bot asks Telegram for messages itself.
        # (Deployed, Telegram calls /api/telegram/webhook instead.)
        background.append(asyncio.create_task(bot.poll_forever()))
    elif settings.bot_mode == "webhook":
        background.append(asyncio.create_task(bot.register_webhook()))
    log.info("AI mode: %s. Telegram bot mode: %s.", settings.ai_mode, settings.bot_mode)
    yield
    for task in background:
        task.cancel()
    jobs.stop()
    db.close()


app = FastAPI(title="Star Boy", lifespan=lifespan)

app.include_router(users.router)
app.include_router(pitches.router)
app.include_router(games.router)
app.include_router(reports.router)
app.include_router(players.router)
app.include_router(home.router)
app.include_router(telegram.router)
app.include_router(settle.router)


@app.get("/api/health")
async def health():
    """Is the server up, and can it reach MongoDB?"""
    return {"status": "ok", "db": await db.ping(), "ai_mode": settings.ai_mode,
            "bot_mode": settings.bot_mode}


# In production (Docker) there is no Vite dev server: FastAPI serves the built
# React app. This route must stay LAST so it never hides an /api route.
@app.get("/{path:path}", include_in_schema=False)
async def frontend(path: str):
    if path.startswith("api/") or not FRONTEND_DIST.is_dir():
        raise HTTPException(status_code=404)
    # A real file (JS, CSS, icon...) is sent as it is. Anything else is a page
    # inside the React app (e.g. /game/123), so it gets index.html.
    file = (FRONTEND_DIST / path).resolve()
    if file.is_file() and file.is_relative_to(FRONTEND_DIST):
        return FileResponse(file)
    return FileResponse(FRONTEND_DIST / "index.html")
