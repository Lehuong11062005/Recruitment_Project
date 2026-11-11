import asyncio
import inspect
from urllib.parse import urlsplit, urlunsplit

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import websockets
from websockets.exceptions import ConnectionClosed

from app.config import settings

router = APIRouter()


def build_core_ws_url(path: str, query: str = "") -> str:
    """Chuyển CORE_URL (http/https) sang ws/wss kèm path và query string (?token=...)."""
    parsed = urlsplit(settings.CORE_URL.rstrip("/"))
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    base_path = parsed.path.rstrip("/")
    clean_path = path.lstrip("/")
    full_path = f"{base_path}/ws/{clean_path}" if clean_path else f"{base_path}/ws"
    return urlunsplit((ws_scheme, parsed.netloc, full_path, query or "", ""))


def _connect_kwargs(headers: dict) -> dict:
    """Tương thích cả websockets >= 14 (additional_headers) và bản cũ (extra_headers)."""
    if not headers:
        return {}
    params = inspect.signature(websockets.connect).parameters
    if "additional_headers" in params:
        return {"additional_headers": headers}
    if "extra_headers" in params:
        return {"extra_headers": headers}
    return {}


async def connect_upstream_ws(url: str, headers: dict):
    return websockets.connect(url, **_connect_kwargs(headers))


@router.websocket("/ws/{path:path}")
async def proxy_core_websocket(websocket: WebSocket, path: str):
    """Chuyển tiếp kết nối WebSocket (vd: /ws/chat/{conversation_id}?token={jwt}) xuống Core Service."""
    target_url = build_core_ws_url(path, websocket.url.query)

    forward_headers = {}
    auth_header = websocket.headers.get("authorization")
    if auth_header:
        forward_headers["Authorization"] = auth_header

    await websocket.accept()

    try:
        upstream_cm = await connect_upstream_ws(target_url, forward_headers)
        async with upstream_cm as upstream:
            async def client_to_upstream():
                try:
                    while True:
                        message = await websocket.receive()
                        msg_type = message.get("type")
                        if msg_type == "websocket.disconnect":
                            break
                        if message.get("text") is not None:
                            await upstream.send(message["text"])
                        elif message.get("bytes") is not None:
                            await upstream.send(message["bytes"])
                except WebSocketDisconnect:
                    pass

            async def upstream_to_client():
                try:
                    async for data in upstream:
                        if isinstance(data, bytes):
                            await websocket.send_bytes(data)
                        else:
                            await websocket.send_text(str(data))
                except ConnectionClosed as exc:
                    try:
                        await websocket.close(code=exc.rcvd.code if exc.rcvd else 1000)
                    except RuntimeError:
                        pass

            tasks = [
                asyncio.create_task(client_to_upstream()),
                asyncio.create_task(upstream_to_client()),
            ]
            done, pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            await asyncio.gather(*done, return_exceptions=True)
    except Exception:
        try:
            await websocket.close(code=1011, reason="Core Service WebSocket unavailable")
        except RuntimeError:
            pass
