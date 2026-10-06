"""Star Boy backend: the API, plus (once built) the React app itself."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from . import db
from .config import FRONTEND_DIST


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once when the server starts, and once when it stops.
    db.connect()
    yield
    db.close()


app = FastAPI(title="Star Boy", lifespan=lifespan)


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
