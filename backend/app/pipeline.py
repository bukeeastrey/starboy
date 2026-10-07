"""The "How was your game?" job: voice note -> transcript -> checked stats."""

import time
from pathlib import Path

from . import extract, jobs, llm, speech
from .db import get_db

# Fewer words than this can't be a match report.
MIN_WORDS = 3


@jobs.handler("transcribe_extract")
async def transcribe_extract(job: dict) -> dict:
    data = job["input"]
    db = get_db()
    timings = {}

    # Who played? Whisper gets the names to spell them right, and Gemma's
    # "assisted Emeka" is matched against them.
    game = await db.games.find_one({"_id": data["game_id"]})
    in_ids = [invite["user_id"] for invite in game["invites"] if invite["status"] == "in"]
    users = await db.users.find({"_id": {"$in": in_ids}}).to_list(None)
    others = [
        {"id": str(user["_id"]), "name": user["name"], "nickname": user.get("nickname", "")}
        for user in users if user["_id"] != data["user_id"]
    ]

    transcript = data.get("text") or ""
    if data.get("audio_path"):
        audio = Path(data["audio_path"])
        try:
            await jobs.set_stage(job["_id"], "listening" if speech.is_loaded() else "warming_up")
            started = time.perf_counter()
            transcript = await speech.transcribe(audio, [user["name"] for user in users])
            timings["whisper_s"] = round(time.perf_counter() - started, 1)
        finally:
            # We never keep voice notes: only the transcript.
            audio.unlink(missing_ok=True)

    if len(transcript.split()) < MIN_WORDS:
        return {"empty": True}

    await jobs.set_stage(job["_id"], "thinking" if await llm.model_loaded() else "warming_up")
    started = time.perf_counter()
    extracted = await extract.extract_stats(transcript, others)
    timings["gemma_s"] = round(time.perf_counter() - started, 1)

    return {"transcript": transcript, **extracted, "timings": timings}
