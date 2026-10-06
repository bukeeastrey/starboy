"""Star Boy backend: the API, plus (once built) the React app itself."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from . import db, setup
from .config import FRONTEND_DIST
from .routes import games, home, pitches, users

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("starboy")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once when the server starts, and once when it stops.
    db.connect()
    try:
        await setup.ensure_indexes()
        await setup.seed_pitches()
    except Exception as error:
        # Keep the server up so /api/health can say what is wrong.
        log.error("Database setup failed: %s", type(error).__name__)
    yield
    db.close()


app = FastAPI(title="Star Boy", lifespan=lifespan)

app.include_router(users.router)
app.include_router(pitches.router)
app.include_router(games.router)
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
