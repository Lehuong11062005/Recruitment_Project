import asyncio
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from websockets.exceptions import ConnectionClosedError
from websockets.frames import Close

from app.main import app
from app.proxy import ws_proxy


class _FakeUpstreamWS:
    def __init__(self, incoming=None, close_exc=None, echo_prefix=None):
        self.sent = []
        self._queue = asyncio.Queue()
        for item in (["reply:hello"] if incoming is None else incoming):
            self._queue.put_nowait(item)
        self._close_exc = close_exc
        self._echo_prefix = echo_prefix
        if close_exc is not None or echo_prefix is None:
            self._queue.put_nowait(StopAsyncIteration)
        self.close_code = 1000
        self.close_reason = ""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def send(self, data):
        self.sent.append(data)
        if self._echo_prefix is not None:
            await self._queue.put(f"{self._echo_prefix}{data}")
            await self._queue.put(StopAsyncIteration)

    def __aiter__(self):
        return self

    async def __anext__(self):
        item = await self._queue.get()
        if item is StopAsyncIteration:
            if self._close_exc is not None:
                raise self._close_exc
            raise StopAsyncIteration
        return item


def test_build_core_ws_url_converts_scheme_and_preserves_query(monkeypatch):
    monkeypatch.setattr(ws_proxy.settings, "CORE_URL", "http://localhost:8001")
    url = ws_proxy.build_core_ws_url("chat/conv-123", "token=abc.def.ghi")
    assert url == "ws://localhost:8001/ws/chat/conv-123?token=abc.def.ghi"

    monkeypatch.setattr(ws_proxy.settings, "CORE_URL", "https://core.example.com")
    wss_url = ws_proxy.build_core_ws_url("/chat/conv-456", "token=xyz")
    assert wss_url == "wss://core.example.com/ws/chat/conv-456?token=xyz"


def test_websocket_proxy_forwards_messages_query_and_auth_header(monkeypatch):
    captured = {}
    fake_upstream = _FakeUpstreamWS(incoming=[], echo_prefix="echo:")

    async def fake_connect(url, headers):
        captured["url"] = url
        captured["headers"] = headers
        return fake_upstream

    monkeypatch.setattr(ws_proxy.settings, "CORE_URL", "http://localhost:8001")
    monkeypatch.setattr(ws_proxy, "connect_upstream_ws", fake_connect)

    client = TestClient(app)
    with client.websocket_connect(
        "/ws/chat/conv-999?token=jwt-token-xyz",
        headers={"Authorization": "Bearer header-token"},
    ) as ws:
        ws.send_text('{"event":"ping"}')
        reply = ws.receive_text()
        assert reply == 'echo:{"event":"ping"}'

    assert captured["url"] == "ws://localhost:8001/ws/chat/conv-999?token=jwt-token-xyz"
    assert captured["headers"] == {"Authorization": "Bearer header-token"}
    assert fake_upstream.sent == ['{"event":"ping"}']


def test_websocket_proxy_propagates_upstream_auth_close_code(monkeypatch):
    close_err = ConnectionClosedError(Close(4401, "Unauthorized"), None)
    fake_upstream = _FakeUpstreamWS(incoming=[], close_exc=close_err)

    async def fake_connect(_url, _headers):
        return fake_upstream

    monkeypatch.setattr(ws_proxy.settings, "CORE_URL", "http://localhost:8001")
    monkeypatch.setattr(ws_proxy, "connect_upstream_ws", fake_connect)

    client = TestClient(app)
    try:
        with client.websocket_connect("/ws/chat/conv-999?token=bad") as ws:
            ws.receive_text()
        raise AssertionError("Expected WebSocketDisconnect with 4401")
    except WebSocketDisconnect as exc:
        assert exc.code == 4401


def test_gateway_http_root_still_healthy():
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Api-gateway" in resp.json().get("messager", "")
