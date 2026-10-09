""""How was your game?": send a voice note or text, check the stats, submit."""

import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from .. import consensus, jobs, notify, played_like, summary
from ..auth import current_user
from ..config import AUDIO_DIR
from ..db import get_db
from ..extract import clean_stats
from ..util import now, oid
from .games import game_phase, invite_of, load_game

router = APIRouter(prefix="/api")

# 90 seconds of phone audio is well under 2 MB; this leaves plenty of room.
MAX_AUDIO_BYTES = 6 * 1024 * 1024
MIN_AUDIO_BYTES = 2000
MAX_TEXT_CHARS = 1000


class TextReport(BaseModel):
    text: str


class ClaimBody(BaseModel):
    transcript: str = ""
    stats: dict
    assisted_player_ids: list[str] = []
    # True = "ask for an edit" of a report teammates already confirmed.
    edit: bool = False
    # Who they vote Man of the Match (another player who was in), or "".
    motm_vote_id: str = ""
    # How the report was made: "voice", "text" or "buttons".
    source: str = "voice"


async def reportable_game(game_id: str, user: dict) -> dict:
    """The game, if this player may report on it. Otherwise a clear error."""
    game, _ = await load_game(game_id)
    if game["status"] == "cancelled":
        raise HTTPException(400, "This game was cancelled.")
    if game_phase(game) == "upcoming":
        raise HTTPException(400, "The game never start! Come back after kickoff.")
    invite = invite_of(game, user["_id"])
    if not invite or invite["status"] != "in":
        raise HTTPException(403, "Tap “I'm in” on the game first, then tell Star Boy how it went.")
    return game


async def queue_report(game: dict, user: dict, **job_input) -> dict:
    """Queue the AI job, unless this player already has one running."""
    busy = await get_db().jobs.find_one(
        {"input.user_id": user["_id"], "status": {"$in": ["queued", "running"]}}
    )
    if busy:
        raise HTTPException(429, "Star Boy is still working on your last report. One moment!")
    job_id = await jobs.enqueue(
        "transcribe_extract", {"game_id": game["_id"], "user_id": user["_id"], **job_input}
    )
    return {"job_id": job_id}


@router.post("/games/{game_id}/report/audio")
async def report_audio(game_id: str, file: UploadFile, user: dict = Depends(current_user)):
    game = await reportable_game(game_id, user)

    audio = await file.read(MAX_AUDIO_BYTES + 1)
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(413, "That voice note is too long. Keep it under 90 seconds.")
    if len(audio) < MIN_AUDIO_BYTES:
        raise HTTPException(400, "I didn't catch that. Try again or type it.")

    # The file lives only until the job has transcribed it (see pipeline.py).
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    path = AUDIO_DIR / f"{uuid.uuid4().hex}.audio"
    path.write_bytes(audio)
    try:
        return await queue_report(game, user, audio_path=str(path))
    except Exception:
        path.unlink(missing_ok=True)
        raise


@router.post("/games/{game_id}/report/text")
async def report_text(game_id: str, body: TextReport, user: dict = Depends(current_user)):
    game = await reportable_game(game_id, user)
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "Type how your game went first.")
    return await queue_report(game, user, text=text[:MAX_TEXT_CHARS])


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, user: dict = Depends(current_user)):
    """The app calls this every couple of seconds until the job is done."""
    db = get_db()
    job = await db.jobs.find_one({"_id": oid(job_id), "input.user_id": user["_id"]})
    if not job:
        raise HTTPException(404, "Not found.")

    view = {"status": job["status"], "stage": job.get("stage", "queued")}
    if job["status"] == "queued":
        # How many jobs are in front of this one.
        view["ahead"] = await db.jobs.count_documents(
            {"status": {"$in": ["queued", "running"]}, "created_at": {"$lt": job["created_at"]}}
        )
    elif job["status"] == "done":
        view["result"] = job["result"]
    elif job["status"] == "error":
        view["error"] = "I couldn't make that out. Try another voice note or type it 🙏"
    return view


@router.post("/games/{game_id}/claim")
async def submit_claim(game_id: str, body: ClaimBody, user: dict = Depends(current_user)):
    """Save the stats the player checked. They stay "pending" until teammates confirm."""
    game = await reportable_game(game_id, user)
    claim = await save_claim(game, user, body.transcript, body.stats,
                             body.assisted_player_ids, edit=body.edit,
                             motm_vote_id=body.motm_vote_id, source=body.source)
    return {"status": "pending", "stats": claim["stats"]}


async def save_claim(game: dict, user: dict, transcript: str, raw_stats: dict,
                     assisted_player_ids: list[str], edit: bool = False,
                     motm_vote_id: str = "", source: str = "voice") -> dict:
    """Save a player's report as a pending claim and ask teammates to confirm.
    Used by the web app and by the Telegram bot (voice, text and tap flows)."""
    db = get_db()

    existing = await db.claims.find_one({"game_id": game["_id"], "user_id": user["_id"]})
    if existing and existing["status"] == "confirmed" and not edit:
        raise HTTPException(409, "Your teammates already confirmed your stats for this game.")

    # Check the numbers again: the player may have edited the card.
    stats = clean_stats(raw_stats)

    # Assisted players must be other players who were in this game.
    in_ids = {invite["user_id"] for invite in game["invites"] if invite["status"] == "in"}
    wanted = {oid(player_id) for player_id in assisted_player_ids}
    assisted = await db.users.find(
        {"_id": {"$in": list((wanted & in_ids) - {user["_id"]})}}
    ).to_list(None)
    stats["assisted_players"] = [{"id": str(u["_id"]), "name": u["name"]} for u in assisted]

    # The Man of the Match vote: another player who was in this game.
    voted_for = None
    if motm_vote_id:
        candidate = oid(motm_vote_id)
        if candidate in in_ids and candidate != user["_id"]:
            voted_for = await db.users.find_one({"_id": candidate})
    stats["motm_vote"] = voted_for and {"id": str(voted_for["_id"]), "name": voted_for["name"]}

    claim = {
        "game_id": game["_id"],
        "user_id": user["_id"],
        "transcript": transcript.strip()[:MAX_TEXT_CHARS],
        "stats": stats,
        "source": source if source in ("voice", "text", "buttons") else "voice",
        # Kept as a real id too, so pipelines can count the votes.
        "motm_vote_id": voted_for["_id"] if voted_for else None,
        "status": "pending",
        "confirmations": [],
        "disputes": [],
        "created_at": now(),
        "confirmed_at": None,
    }
    # A new report replaces the player's earlier one and needs confirming again.
    await db.claims.replace_one(
        {"game_id": game["_id"], "user_id": user["_id"]}, claim, upsert=True
    )
    if existing and existing["status"] == "confirmed":
        await consensus.check_numbers(game["_id"])  # their old numbers no longer count

    # Ask the other players on Telegram (in the background).
    saved = await db.claims.find_one({"game_id": game["_id"], "user_id": user["_id"]})
    asyncio.create_task(notify.claim_to_teammates(saved, game, user))
    # "You played like...": the code picks the legend, Gemma writes the line.
    saved["played_like"] = await played_like.choose_for(saved)
    # Enough reports in? Then Star Boy writes (or rewrites) the game summary.
    await summary.maybe_queue(game["_id"])
    return saved
