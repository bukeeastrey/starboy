"""Photos from the crew: match galleries, pitch covers and profile pictures.

The image bytes live in MongoDB GridFS (a bucket called "photos"), so
everything stays in Atlas and nothing needs a second service. Every photo is
stored twice: "full" (about 1280 px, ~200 KB) and "thumb" (about 320 px).
The browser makes both sizes before uploading; the server has no image library.

The free server has a small data allowance, so lists show thumbnails, full
images load only when opened, and browsers are told to keep both for a year."""

from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from .db import get_db
from .util import now

MAX_FULL_BYTES = 700_000
MAX_THUMB_BYTES = 150_000
MAX_PER_GAME = 40

KINDS = ("game", "cover", "avatar")


def sniff(data: bytes) -> str | None:
    """The image type from its first bytes. We don't trust file names."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    return None


def bucket() -> AsyncIOMotorGridFSBucket:
    return AsyncIOMotorGridFSBucket(get_db(), bucket_name="photos")


def urls(photo_id) -> dict:
    """Where the app loads a photo from."""
    return {"id": str(photo_id),
            "thumb": f"/api/photos/{photo_id}/thumb",
            "full": f"/api/photos/{photo_id}/full"}


async def save(kind: str, user_id, full: bytes, thumb: bytes, *, game_id=None,
               pitch_id=None, source: str = "web") -> dict:
    """Check and store one photo (both sizes). Returns its document."""
    full_type, thumb_type = sniff(full), sniff(thumb)
    if not full_type or not thumb_type:
        raise HTTPException(400, "That file isn't a photo Star Boy can use (JPEG, WebP or PNG).")
    if len(full) > MAX_FULL_BYTES or len(thumb) > MAX_THUMB_BYTES:
        raise HTTPException(413, "That photo is too big. Try another one.")

    files = bucket()
    full_id = await files.upload_from_stream("full", full, metadata={"content_type": full_type})
    thumb_id = await files.upload_from_stream("thumb", thumb, metadata={"content_type": thumb_type})
    photo = {
        "kind": kind, "user_id": user_id, "game_id": game_id, "pitch_id": pitch_id,
        "full_id": full_id, "thumb_id": thumb_id,
        "full_type": full_type, "thumb_type": thumb_type,
        "bytes": len(full) + len(thumb), "source": source, "created_at": now(),
    }
    await get_db().photos.insert_one(photo)
    return photo


async def remove(photo: dict) -> None:
    """Delete a photo's document and both stored files."""
    files = bucket()
    for file_id in (photo["full_id"], photo["thumb_id"]):
        try:
            await files.delete(file_id)
        except Exception:
            pass  # already gone
    await get_db().photos.delete_one({"_id": photo["_id"]})


async def read(photo: dict, size: str) -> tuple[bytes, str]:
    """The bytes and content type of one size of a photo."""
    stream = await bucket().open_download_stream(photo[f"{size}_id"])
    return await stream.read(), photo[f"{size}_type"]


async def game_gallery(game: dict, me: dict, users_by_id: dict) -> list[dict]:
    """A game's photos, newest first, with who added each and whether the
    viewer may delete it (their own, or any if they set the game up)."""
    photos = await get_db().photos.find(
        {"kind": "game", "game_id": game["_id"]}).sort("created_at", -1).to_list(MAX_PER_GAME)
    is_creator = game["created_by"] == me["_id"]
    return [
        {**urls(photo["_id"]),
         "by": (users_by_id.get(photo["user_id"]) or {}).get("name", ""),
         "can_delete": is_creator or photo["user_id"] == me["_id"]}
        for photo in photos
    ]


async def first_for_games(game_ids: list) -> dict:
    """{game_id: photo urls} with one photo per game (the newest), for cards
    that want to show a picture from the match."""
    rows = await get_db().photos.aggregate([
        {"$match": {"kind": "game", "game_id": {"$in": list(game_ids)}}},
        {"$sort": {"created_at": -1}},
        {"$group": {"_id": "$game_id", "photo_id": {"$first": "$_id"}}},
    ]).to_list(None)
    return {row["_id"]: urls(row["photo_id"]) for row in rows}
