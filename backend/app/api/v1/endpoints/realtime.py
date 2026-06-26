from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlmodel import Session, select

from app.core.database import engine
from app.core.security import decode_token
from app.core.token_store import is_token_revoked
from app.core.ws_manager import ws_manager
from app.models.user import User
from app.schemas.auth import TokenPayload


router = APIRouter()


@router.websocket("/scan-events")
async def scan_events_ws(websocket: WebSocket, token: str = Query(...)):
    user = _resolve_user(token)
    if not user:
        await websocket.close(code=4001)
        return

    tenant_id = str(user.tenant_id)
    user_id = str(user.id)
    await ws_manager.connect(websocket, tenant_id, user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(websocket, tenant_id, user_id)


def _resolve_user(token: str) -> User | None:
    try:
        payload = decode_token(token)
        token_data = TokenPayload(sub=payload.get("sub"))
        if token_data.sub is None or payload.get("type") != "access":
            return None
        jti = payload.get("jti")
        if not jti or is_token_revoked(jti):
            return None
        from uuid import UUID
        user_id = UUID(token_data.sub)
        with Session(engine) as session:
            return session.exec(select(User).where(User.id == user_id)).first()
    except Exception:
        return None
