from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.token_store import count_online_users, mark_user_online
from app.models.user import User


router = APIRouter()


@router.post("/heartbeat")
def heartbeat(current_user: User = Depends(get_current_user)) -> dict[str, str]:
    mark_user_online(str(current_user.tenant_id), str(current_user.id))
    return {"status": "ok"}


@router.get("/online")
def online_users(current_user: User = Depends(get_current_user)) -> dict[str, int]:
    return {"online_users": count_online_users(str(current_user.tenant_id))}