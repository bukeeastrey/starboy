"""Small helpers used all over the backend."""

from datetime import datetime, timedelta, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException

# Nigeria is on West Africa Time all year: UTC+1, no daylight saving.
WAT = timezone(timedelta(hours=1), "WAT")


def now() -> datetime:
    """The current time in UTC (what we store in MongoDB)."""
    return datetime.now(timezone.utc)


def oid(value: str) -> ObjectId:
    """Turn an id from a URL into a MongoDB ObjectId, or answer 404."""
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Not found.")


def public_user(user: dict) -> dict:
    """What OTHER people may see of a user. Never the phone number."""
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "nickname": user.get("nickname", ""),
        "position": user.get("position", "Anywhere"),
    }


def display_name(user: dict) -> str:
    """Nickname if they have one, otherwise the first name."""
    return user.get("nickname") or user["name"].split()[0]


def format_kickoff(when: datetime) -> str:
    """A UTC time as people in Lagos say it: 'Fri 9 Oct, 5:00 pm'."""
    local = when.astimezone(WAT)
    hour = local.hour % 12 or 12
    am_pm = "am" if local.hour < 12 else "pm"
    return f"{local:%a} {local.day} {local:%b}, {hour}:{local:%M} {am_pm}"
