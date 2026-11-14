"""Task 10.3 (UC-C8 & UC-R7): REST + WebSocket chat realtime giữa HR và ứng viên.

REST  (prefix /api/v1/conversations, qua Gateway :8000):
    POST ""                    tạo/lấy phòng chat theo job_id
    GET  ""                    danh sách hội thoại của tôi
    GET  "/{id}/messages"      lịch sử tin nhắn
WS    ws://localhost:8001/ws/chat/{conversation_id}?token={jwt}   (nối thẳng core-service)

Giao thức WebSocket (JSON):
    client -> server  {"event":"message","message_type":"TEXT","content":"Xin chào","attachments":[]}
                      {"event":"read"}   |   {"event":"ping"}
                      (thiếu "event" thì coi là "message")
    server -> client  {"event":"message","data":{...MessageResponse}}   (gửi cho CẢ người gửi lẫn người nhận)
                      {"event":"read","data":{"conversation_id":..,"reader_id":..}}
                      {"event":"pong"}  |  {"event":"error","detail":"..."}
    Đóng kết nối: 4401 = token sai/hết hạn, 4403 = không phải thành viên phòng, 4404 = không có phòng.
"""
import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Set

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.core.deps import get_current_user
from app.core.security import JWTError, decode_access_token
from app.models.user import User
from app.schemas.chat import (
    ConversationCreate,
    ConversationResponse,
    MessageResponse,
    WSIncomingMessage,
)
from app.services import chat_service
from app.services.chat_service import ChatError

logger = logging.getLogger(__name__)

router = APIRouter()      # REST
ws_router = APIRouter()   # WebSocket (không có prefix /api/v1)


# ===================== REST =====================
def _parse_oid(value: str, name: str) -> PydanticObjectId:
    try:
        return PydanticObjectId(value)
    except Exception:
        raise HTTPException(422, f"{name} không hợp lệ")


@router.post("", response_model=ConversationResponse,
             summary="Tạo hoặc lấy phòng chat giữa HR và ứng viên theo job_id")
async def create_or_get_conversation(body: ConversationCreate, user: User = Depends(get_current_user)):
    try:
        conv = await chat_service.get_or_create_conversation(user, body.job_id, body.candidate_id)
    except ChatError as exc:
        raise HTTPException(exc.status_code, exc.message)
    # Dựng response đầy đủ (tên đối phương, job_title, unread) bằng cách tái dùng hàm list
    for item in await chat_service.list_conversations(user):
        if item.id == conv.id:
            return item
    raise HTTPException(500, "Không dựng được dữ liệu hội thoại")


@router.get("", response_model=List[ConversationResponse],
            summary="Danh sách hội thoại của tôi (mới cập nhật trước)")
async def list_my_conversations(user: User = Depends(get_current_user)):
    return await chat_service.list_conversations(user)


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse],
            summary="Lịch sử tin nhắn (cũ -> mới); tự đánh dấu đã đọc tin của người kia")
async def get_messages(
    conversation_id: str,
    limit: int = Query(50, ge=1, le=100),
    before: Optional[datetime] = Query(None, description="Chỉ lấy tin cũ hơn mốc này (phân trang ngược)"),
    user: User = Depends(get_current_user),
):
    oid = _parse_oid(conversation_id, "conversation_id")
    try:
        return await chat_service.list_messages(user, oid, limit, before)
    except ChatError as exc:
        raise HTTPException(exc.status_code, exc.message)


# ===================== WebSocket =====================
class ConnectionManager:
    """Quản lý các kết nối theo phòng. Lưu trong RAM => chỉ đúng khi chạy 1 worker uvicorn."""

    def __init__(self) -> None:
        self.rooms: Dict[str, Set[WebSocket]] = defaultdict(set)

    def connect(self, room: str, ws: WebSocket) -> None:
        self.rooms[room].add(ws)

    def disconnect(self, room: str, ws: WebSocket) -> None:
        self.rooms[room].discard(ws)
        if not self.rooms[room]:
            self.rooms.pop(room, None)

    async def broadcast(self, room: str, payload: dict) -> None:
        for ws in list(self.rooms.get(room, ())):
            try:
                await ws.send_json(payload)
            except Exception:  # noqa: BLE001 - kết nối chết thì gỡ ra
                self.disconnect(room, ws)


manager = ConnectionManager()


async def _user_from_token(token: str) -> Optional[User]:
    """Browser không gửi được header Authorization cho WebSocket nên đọc JWT từ query ?token=."""
    if not token:
        return None
    try:
        user_id = PydanticObjectId(decode_access_token(token).get("sub"))
    except (JWTError, Exception):
        return None
    user = await User.get(user_id)
    if user is None or user.deleted_at is not None or user.status != "ACTIVE":
        return None
    return user


@ws_router.websocket("/ws/chat/{conversation_id}")
async def chat_websocket(websocket: WebSocket, conversation_id: str, token: str = Query(default="")):
    await websocket.accept()   # accept trước rồi mới close để frontend đọc được mã lỗi 44xx

    user = await _user_from_token(token)
    if user is None:
        await websocket.close(code=4401, reason="Unauthorized")
        return
    try:
        conv = await chat_service.get_conversation_for_user(user, PydanticObjectId(conversation_id))
    except ChatError:
        await websocket.close(code=4404, reason="Conversation not found")
        return
    except Exception:
        await websocket.close(code=4404, reason="Invalid conversation id")
        return

    room = str(conv.id)
    manager.connect(room, websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
                if not isinstance(data, dict):
                    raise ValueError
            except ValueError:
                await websocket.send_json({"event": "error", "detail": "Dữ liệu phải là JSON object"})
                continue

            event = data.get("event", "message")
            if event == "ping":
                await websocket.send_json({"event": "pong"})
            elif event == "read":
                await chat_service.mark_read(conv, user)
                await manager.broadcast(room, {
                    "event": "read", "data": {"conversation_id": room, "reader_id": str(user.id)},
                })
            elif event == "message":
                try:
                    incoming = WSIncomingMessage(**{k: v for k, v in data.items() if k != "event"})
                    message = await chat_service.save_message(
                        conv, user, incoming.message_type, incoming.content, incoming.attachments
                    )
                except ValidationError as exc:
                    first = exc.errors()[0]
                    await websocket.send_json({"event": "error", "detail": f"{first['loc'][-1]}: {first['msg']}"})
                    continue
                except ChatError as exc:
                    await websocket.send_json({"event": "error", "detail": exc.message})
                    continue
                await manager.broadcast(room, {
                    "event": "message",
                    "data": chat_service.to_message_response(message).model_dump(mode="json"),
                })
            else:
                await websocket.send_json({"event": "error", "detail": f"Event không hỗ trợ: {event}"})
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        logger.exception("Lỗi WebSocket chat (phòng %s)", room)
        try:
            await websocket.close(code=1011)
        except Exception:  # noqa: BLE001
            pass
    finally:
        manager.disconnect(room, websocket)
