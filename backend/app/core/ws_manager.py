import asyncio
import json
import logging
from typing import Any

import redis as sync_redis
from fastapi import WebSocket

from app.core.config import settings

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self._by_tenant: dict[str, dict[str, set[WebSocket]]] = {}
        self._listener_task: asyncio.Task | None = None

    async def connect(self, ws: WebSocket, tenant_id: str, user_id: str) -> None:
        await ws.accept()
        self._by_tenant.setdefault(tenant_id, {})
        self._by_tenant[tenant_id].setdefault(user_id, set()).add(ws)
        if self._listener_task is None:
            self._listener_task = asyncio.create_task(self._redis_listener())

    def disconnect(self, ws: WebSocket, tenant_id: str, user_id: str) -> None:
        user_sockets = self._by_tenant.get(tenant_id, {}).get(user_id, set())
        user_sockets.discard(ws)
        if not user_sockets:
            self._by_tenant[tenant_id].pop(user_id, None)
        if not self._by_tenant.get(tenant_id):
            self._by_tenant.pop(tenant_id, None)

    async def send_to_user(self, tenant_id: str, user_id: str, event: dict[str, Any]) -> None:
        message = json.dumps(event)
        user_sockets = self._by_tenant.get(tenant_id, {}).get(user_id, set())
        for ws in list(user_sockets):
            try:
                await ws.send_text(message)
            except Exception:
                user_sockets.discard(ws)

    async def broadcast_tenant(self, tenant_id: str, event: dict[str, Any]) -> None:
        message = json.dumps(event)
        for user_sockets in self._by_tenant.get(tenant_id, {}).values():
            for ws in list(user_sockets):
                try:
                    await ws.send_text(message)
                except Exception:
                    user_sockets.discard(ws)

    async def _redis_listener(self) -> None:
        while True:
            try:
                r = sync_redis.from_url(settings.redis_url, decode_responses=True)
                pubsub = r.pubsub()
                pubsub.subscribe("scan:progress", "scan:completed", "ai:completed")
                while True:
                    message = pubsub.get_message(timeout=1.0)
                    if message and message["type"] == "message":
                        try:
                            data = json.loads(message["data"])
                            await self._route_event(data)
                        except Exception:
                            logger.exception("Failed to process Redis message")
                    await asyncio.sleep(0.01)
            except Exception:
                logger.exception("Redis listener error, reconnecting in 5s")
                await asyncio.sleep(5)

    async def _route_event(self, data: dict) -> None:
        tenant_id = data.get("tenant_id")
        user_id = data.get("user_id")
        if user_id and tenant_id:
            await self.send_to_user(tenant_id, user_id, data)
        elif tenant_id:
            await self.broadcast_tenant(tenant_id, data)
        else:
            for tid in list(self._by_tenant.keys()):
                await self.broadcast_tenant(tid, data)


ws_manager = WebSocketManager()
