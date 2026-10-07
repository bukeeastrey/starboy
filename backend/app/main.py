"""Star Boy backend: the API, plus (once built) the React app itself."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from . import db, jobs, llm, prompts, setup
from . import pipeline  # noqa: F401  (importing it registers the AI job)
from .config import AUDIO_DIR, FRONTEND_DIST
from .routes import games, home, pitches, players, reports, users

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
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
    # Load Gemma in the background so the first voice note isn't the slow one.
    warm_up = asyncio.create_task(llm.warm_up(prompts.EXTRACT_SYSTEM))
    yield
    warm_up.cancel()
    jobs.stop()
    db.close()


app = FastAPI(title="Star Boy", lifespan=lifespan)

app.include_router(users.router)
app.include_router(pitches.router)
app.include_router(games.router)
app.include_router(reports.router)
app.include_router(players.router)
app.include_router(home.router)


@app.get("/api/health")
async def health():
    """Is the server up, and can it reach MongoDB?"""
    return {"status": "ok", "db": await db.ping()}


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
