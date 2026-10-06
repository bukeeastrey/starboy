"""Everything the Home screen needs, in one request."""

from fastapi import APIRouter, Depends

from ..auth import current_user
from .pitches import pitches_for

router = APIRouter(prefix="/api")


@router.get("/home")
async def home(user: dict = Depends(current_user)):
    return {
        "pitches": await pitches_for(user, only_mine=True),
    }
