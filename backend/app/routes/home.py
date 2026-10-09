"""Everything the Home screen needs, in one request."""

from fastapi import APIRouter, Depends

from ..auth import current_user
from .games import my_next_games, my_recent_games, my_unreported_games
from .pitches import pitches_for

router = APIRouter(prefix="/api")


@router.get("/home")
async def home(user: dict = Depends(current_user)):
    return {
        "next_games": await my_next_games(user),
        "needs_report": await my_unreported_games(user),
        "recent_games": await my_recent_games(user),
        "pitches": await pitches_for(user, only_mine=True),
    }
