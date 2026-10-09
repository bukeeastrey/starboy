"""Uploading, showing and deleting photos."""

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile

from .. import photos
from ..auth import current_user
from ..db import get_db
from ..util import oid
from .games import invite_of, load_game

router = APIRouter(prefix="/api")

# A photo never changes once stored, so the browser may keep it for a year
# and never ask again. "private": only the signed-in player's own browser.
CACHE_FOREVER = "private, max-age=31536000, immutable"


async def read_upload(full: UploadFile, thumb: UploadFile) -> tuple[bytes, bytes]:
    """Read both sizes, refusing anything over the limit before storing it."""
    full_bytes = await full.read(photos.MAX_FULL_BYTES + 1)
    thumb_bytes = await thumb.read(photos.MAX_THUMB_BYTES + 1)
    return full_bytes, thumb_bytes


@router.post("/games/{game_id}/photos")
async def add_game_photo(game_id: str, full: UploadFile, thumb: UploadFile,
                         user: dict = Depends(current_user)):
    """Add a match photo to a game's gallery. For players who were in."""
    game, _ = await load_game(game_id)
    invite = invite_of(game, user["_id"])
    if game["created_by"] != user["_id"] and (not invite or invite["status"] != "in"):
        raise HTTPException(403, "Only players who were in this game can add photos.")
    count = await get_db().photos.count_documents({"kind": "game", "game_id": game["_id"]})
    if count >= photos.MAX_PER_GAME:
        raise HTTPException(400, f"This game already has {photos.MAX_PER_GAME} photos.")

    full_bytes, thumb_bytes = await read_upload(full, thumb)
    photo = await photos.save("game", user["_id"], full_bytes, thumb_bytes,
                              game_id=game["_id"], pitch_id=game["pitch_id"])
    return {**photos.urls(photo["_id"]), "by": user["name"], "can_delete": True}


@router.post("/pitches/{pitch_id}/cover")
async def set_pitch_cover(pitch_id: str, full: UploadFile, thumb: UploadFile,
                          user: dict = Depends(current_user)):
    """Set or replace a pitch's cover photo. For players registered there."""
    db = get_db()
    pitch = await db.pitches.find_one({"_id": oid(pitch_id)})
    if not pitch:
        raise HTTPException(404, "We can't find that pitch.")
    if not await db.registrations.find_one({"pitch_id": pitch["_id"], "user_id": user["_id"]}):
        raise HTTPException(403, "Register at this pitch first, then you can set its photo.")

    full_bytes, thumb_bytes = await read_upload(full, thumb)
    photo = await photos.save("cover", user["_id"], full_bytes, thumb_bytes, pitch_id=pitch["_id"])
    await db.pitches.update_one({"_id": pitch["_id"]}, {"$set": {"cover_photo_id": photo["_id"]}})
    await remove_old(pitch.get("cover_photo_id"))
    return photos.urls(photo["_id"])


@router.post("/me/photo")
async def set_my_photo(full: UploadFile, thumb: UploadFile, user: dict = Depends(current_user)):
    """Set or replace your profile photo (shown on your player card)."""
    full_bytes, thumb_bytes = await read_upload(full, thumb)
    photo = await photos.save("avatar", user["_id"], full_bytes, thumb_bytes)
    await get_db().users.update_one({"_id": user["_id"]}, {"$set": {"avatar_photo_id": photo["_id"]}})
    await remove_old(user.get("avatar_photo_id"))
    return photos.urls(photo["_id"])


@router.delete("/me/photo")
async def remove_my_photo(user: dict = Depends(current_user)):
    await get_db().users.update_one({"_id": user["_id"]}, {"$set": {"avatar_photo_id": None}})
    await remove_old(user.get("avatar_photo_id"))
    return {"ok": True}


async def remove_old(photo_id) -> None:
    """A replaced cover or profile photo is deleted, so storage doesn't fill up."""
    if photo_id:
        old = await get_db().photos.find_one({"_id": photo_id})
        if old:
            await photos.remove(old)


@router.delete("/photos/{photo_id}")
async def delete_photo(photo_id: str, user: dict = Depends(current_user)):
    """Players delete their own photos; a game's creator can remove any from that game."""
    db = get_db()
    photo = await db.photos.find_one({"_id": oid(photo_id)})
    if not photo:
        raise HTTPException(404, "That photo is already gone.")
    allowed = photo["user_id"] == user["_id"]
    if not allowed and photo["kind"] == "game":
        game = await db.games.find_one({"_id": photo["game_id"]})
        allowed = bool(game) and game["created_by"] == user["_id"]
    if not allowed:
        raise HTTPException(403, "You can only delete your own photos.")

    if photo["kind"] == "cover":
        await db.pitches.update_one({"cover_photo_id": photo["_id"]}, {"$set": {"cover_photo_id": None}})
    if photo["kind"] == "avatar":
        await db.users.update_one({"avatar_photo_id": photo["_id"]}, {"$set": {"avatar_photo_id": None}})
    await photos.remove(photo)
    return {"ok": True}


@router.get("/photos/{photo_id}/{size}")
async def get_photo(photo_id: str, size: str, user: dict = Depends(current_user)):
    """The image itself. Only for signed-in players: these are people's photos."""
    if size not in ("thumb", "full"):
        raise HTTPException(404, "Not found.")
    photo = await get_db().photos.find_one({"_id": oid(photo_id)})
    if not photo:
        raise HTTPException(404, "Not found.")
    data, content_type = await photos.read(photo, size)
    return Response(data, media_type=content_type, headers={"Cache-Control": CACHE_FOREVER})
