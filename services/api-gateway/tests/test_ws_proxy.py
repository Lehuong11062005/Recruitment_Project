from fastapi.testclient import TestClient

from app.main import app
from app.proxy import ws_proxy


class _FakeUpstreamWS:
    def __init__(self):
        self.sent = []
        self._incoming = ["reply:hello"]

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def send(self, data):
        self.sent.append(data)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._incoming:
            return self._incoming.pop(0)
        raise StopAsyncIteration


def test_build_core_ws_url_converts_scheme_and_preserves_query(monkeypatch):
    monkeypatch.setattr(ws_proxy.settings, "CORE_URL", "http://localhost:8001")
    url = ws_proxy.build_core_ws_url("chat/conv-123", "token=abc.def.ghi")
    assert url == "ws://localhost:8001/ws/chat/conv-123?token=abc.def.ghi"


def test_websocket_proxy_forwards_messages_and_query(monkeypatch):
    captured = {}
    fake_upstream = _FakeUpstreamWS()

    async def fake_connect(url, headers):
        captured["url"] = url
        captured["headers"] = headers
        return fake_upstream

    monkeypatch.setattr(ws_proxy.settings, "CORE_URL", "http://localhost:8001")
    monkeypatch.setattr(ws_proxy, "connect_upstream_ws", fake_connect)

    client = TestClient(app)
    with client.websocket_connect("/ws/chat/conv-999?token=jwt-token-xyz") as ws:
        ws.send_text("ping")
        reply = ws.receive_text()
        assert reply == "reply:hello"

    assert captured["url"] == "ws://localhost:8001/ws/chat/conv-999?token=jwt-token-xyz"
