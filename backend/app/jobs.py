"""The AI job queue.

Whisper and Gemma are slow on a CPU, so a request never waits for them. It puts
a job in the queue and answers straight away; ONE worker does the jobs one at a
time, and the app asks "is it ready?" every couple of seconds."""

import asyncio
import logging

from bson import ObjectId

from .db import get_db
from .util import now

log = logging.getLogger("starboy.jobs")

_queue: asyncio.Queue = asyncio.Queue()
_handlers = {}  # job type -> the async function that does it
_worker_task: asyncio.Task | None = None


_finished_callbacks = []  # async functions called with each finished job


def on_finished(callback):
    """Decorator: "call this function every time a job finishes"."""
    _finished_callbacks.append(callback)
    return callback


def handler(job_type: str):
    """Decorator: "this function does jobs of this type"."""
    def register(function):
        _handlers[job_type] = function
        return function
    return register


async def enqueue(job_type: str, job_input: dict) -> str:
    """Save a new job, put it in the queue and return its id."""
    job = {
        "type": job_type,
        "status": "queued",
        "stage": "queued",
        "input": job_input,
        "result": None,
        "error": None,
        "created_at": now(),
        "finished_at": None,
    }
    await get_db().jobs.insert_one(job)
    _queue.put_nowait(job["_id"])
    return str(job["_id"])


async def set_stage(job_id: ObjectId, stage: str) -> None:
    """Tell the app what the job is doing now ("listening", "thinking"...)."""
    await get_db().jobs.update_one({"_id": job_id}, {"$set": {"stage": stage}})


async def _worker() -> None:
    db = get_db()
    while True:
        job_id = await _queue.get()
        job = await db.jobs.find_one_and_update(
            {"_id": job_id, "status": "queued"}, {"$set": {"status": "running"}}
        )
        if not job:
            continue
        try:
            result = await _handlers[job["type"]](job)
            update = {"status": "done", "result": result}
        except Exception as error:
            log.exception("Job %s failed", job_id)
            update = {"status": "error", "error": type(error).__name__}
        await db.jobs.update_one(
            {"_id": job_id}, {"$set": {**update, "stage": "finished", "finished_at": now()}}
        )
        # Tell whoever is waiting (the Telegram bot replies to the player).
        for callback in _finished_callbacks:
            try:
                await callback({**job, **update})
            except Exception:
                log.exception("A job-finished callback failed")


async def start() -> None:
    """Called when the server starts."""
    global _worker_task
    # Jobs that were waiting when the server stopped can't be finished (their
    # audio is gone), so mark them failed and let the player send it again.
    try:
        await get_db().jobs.update_many(
            {"status": {"$in": ["queued", "running"]}},
            {"$set": {"status": "error", "error": "ServerRestarted", "finished_at": now()}},
        )
    except Exception as error:
        log.error("Could not clean up old jobs: %s", type(error).__name__)
    # Start the worker even if the database is down right now: it only needs
    # the database once a job arrives.
    _worker_task = asyncio.create_task(_worker())


def stop() -> None:
    if _worker_task:
        _worker_task.cancel()
