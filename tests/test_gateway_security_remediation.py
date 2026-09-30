"""Regression coverage for gateway abuse and fan-out controls."""

from __future__ import annotations

import asyncio
import importlib
from types import SimpleNamespace


def _load_gateway(monkeypatch, *, rate_limit: str = "300", correlations: str = "2"):
    monkeypatch.setenv(
        "GATEWAY_API_KEY", "gateway-test-key-that-is-at-least-32-characters"
    )
    monkeypatch.setenv(
        "MCP_GATEWAY_API_KEY", "mcp-service-key-that-is-at-least-32-characters"
    )
    monkeypatch.setenv(
        "LLM_REDTEAM_API_KEY", "llm-service-key-that-is-at-least-32-characters"
    )
    monkeypatch.setenv(
        "DATASET_POISON_API_KEY", "dataset-service-key-that-is-at-least-32-chars"
    )
    monkeypatch.setenv(
        "MODEL_PRIVACY_API_KEY", "privacy-service-key-that-is-at-least-32-chars"
    )
    monkeypatch.setenv("GATEWAY_RATE_LIMIT_RPM", rate_limit)
    monkeypatch.setenv("GATEWAY_MAX_CONCURRENT_CORRELATIONS", correlations)
    import gateway_server

    return importlib.reload(gateway_server)


def test_gateway_rate_limit_budget_is_enforced(monkeypatch):
    gateway = _load_gateway(monkeypatch, rate_limit="2")
    gateway._rate_windows.clear()

    assert gateway._consume_rate_limit("client-a") is True
    assert gateway._consume_rate_limit("client-a") is True
    assert gateway._consume_rate_limit("client-a") is False
    assert gateway._consume_rate_limit("client-b") is True


def test_correlate_fanout_respects_global_concurrency_budget(monkeypatch):
    gateway = _load_gateway(monkeypatch, correlations="2")
    monkeypatch.setattr(gateway, "SERVICE_URLS", {"mcp_gateway": "http://mcp-gateway:8080"})
    gateway._correlate_slots = asyncio.Semaphore(2)

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"findings": []}

    class Client:
        def __init__(self):
            self.active = 0
            self.max_active = 0

        async def post(self, *args, **kwargs):
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            try:
                await asyncio.sleep(0.03)
                return Response()
            finally:
                self.active -= 1

    async def scenario():
        client = Client()
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(http_client=client)))
        await asyncio.gather(
            *[
                gateway.correlate(
                    request=request,
                    payload={"content": f"sample-{index}"},
                    api_key="gateway-test-key-that-is-at-least-32-characters",
                )
                for index in range(6)
            ]
        )
        assert client.max_active == 2

    asyncio.run(scenario())


def test_invalid_key_rotation_cannot_reset_peer_budget(monkeypatch):
    from fastapi.testclient import TestClient

    gateway = _load_gateway(monkeypatch, rate_limit="2")
    with TestClient(gateway.app) as client:
        assert client.get('/status', headers={'X-API-Key': 'first'}).status_code == 401
        assert client.get('/status', headers={'X-API-Key': 'second'}).status_code == 401
        assert client.get('/status', headers={'X-API-Key': 'third'}).status_code == 429


def test_correlate_body_size_is_capped_before_json_parsing(monkeypatch):
    from fastapi.testclient import TestClient

    gateway = _load_gateway(monkeypatch)
    with TestClient(gateway.app) as client:
        response = client.post('/correlate', content=b'x' * (gateway.MAX_PROXY_BODY_BYTES + 1))
    assert response.status_code == 413


def test_rate_state_has_a_hard_cardinality_bound(monkeypatch):
    gateway = _load_gateway(monkeypatch)
    for index in range(4096):
        assert gateway._consume_rate_limit(str(index))
    assert not gateway._consume_rate_limit('overflow')
    assert len(gateway._rate_windows) == 4096
