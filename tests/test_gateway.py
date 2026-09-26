"""Tests for the unified gateway server.

Covers:
- Health endpoint (unauthenticated)
- API key authentication
- Service routing by path prefix
- Invalid API key rejection
- Explicit upstream header allowlisting
"""

from __future__ import annotations

import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

# A known, valid API key used consistently across this module's fixtures.
VALID_API_KEY = "test-api-key-that-is-at-least-32-characters-long"
INVALID_API_KEY = "invalid-key-definitely-wrong-and-short"


def _load_gateway(monkeypatch):
    """(Re)load gateway_server with distinct external and service credentials."""
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setenv("GATEWAY_API_KEY", VALID_API_KEY)
    monkeypatch.setenv("MCP_GATEWAY_API_KEY", "mcp-gateway-service-key-at-least-32-characters")
    monkeypatch.setenv("LLM_REDTEAM_API_KEY", "llm-redteam-service-key-at-least-32-chars")
    monkeypatch.setenv("DATASET_POISON_API_KEY", "dataset-poison-service-key-at-least-32-chars")
    monkeypatch.setenv("MODEL_PRIVACY_API_KEY", "model-privacy-service-key-at-least-32-characters")
    import gateway_server

    return importlib.reload(gateway_server)


@pytest.fixture
def gateway(monkeypatch):
    """The gateway_server module, freshly reloaded under a known API key."""
    return _load_gateway(monkeypatch)


@pytest.fixture
def app(gateway):
    """The FastAPI app whose auth dependency reads the known API key."""
    return gateway.app


@pytest.fixture
def SERVICES(gateway):
    """The service map from the freshly loaded gateway module."""
    return gateway.SERVICES


from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client(app):
    """Synchronous test client for the gateway (triggers lifespan events)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers():
    """Headers with a valid API key."""
    return {"X-API-Key": VALID_API_KEY}


# ---------------------------------------------------------------------------
# Health endpoint tests
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    """Health endpoint requires no authentication."""

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_healthy_status(self, client):
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_health_no_auth_required(self, client):
        """Health endpoint must work without any API key (load balancer probes)."""
        response = client.get("/health")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# API key authentication tests
# ---------------------------------------------------------------------------


class TestAPIKeyAuth:
    """Verify API key authentication works correctly."""

    def test_valid_api_key_grants_access(self, client, auth_headers):
        response = client.get("/status", headers=auth_headers)
        assert response.status_code == 200

    def test_missing_api_key_returns_401(self, client):
        response = client.get("/status")
        assert response.status_code == 401

    def test_invalid_api_key_returns_401(self, client):
        response = client.get("/status", headers={"X-API-Key": INVALID_API_KEY})
        assert response.status_code == 401

    def test_empty_api_key_returns_401(self, client):
        response = client.get("/status", headers={"X-API-Key": ""})
        assert response.status_code == 401

    def test_401_response_has_detail(self, client):
        response = client.get("/status", headers={"X-API-Key": "wrong"})
        data = response.json()
        assert "detail" in data


# ---------------------------------------------------------------------------
# Service routing tests
# ---------------------------------------------------------------------------


class TestServiceRouting:
    """Verify the gateway routes to correct services based on path prefix."""

    def test_unknown_service_returns_404(self, client, auth_headers):
        response = client.get("/nonexistent_service/health", headers=auth_headers)
        assert response.status_code == 404
        assert "Unknown service" in response.json()["detail"]

    def test_known_services_are_routable(self, client, auth_headers, SERVICES):
        """All configured services should be recognized (not 404).
        They may return 502/504 since backends aren't running, but not 404."""
        for service_name in SERVICES:
            response = client.get(f"/{service_name}/health", headers=auth_headers)
            assert response.status_code != 404, f"{service_name} returned 404"
            assert response.status_code != 401, f"{service_name} returned 401"

    def test_routing_requires_auth(self, client):
        """Service routes require API key authentication."""
        response = client.get("/mcp_gateway/v1/health")
        assert response.status_code == 401

    def test_status_endpoint_lists_services(self, client, auth_headers, SERVICES):
        response = client.get("/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "services" in data
        assert isinstance(data["services"], list)
        assert len(data["services"]) == len(SERVICES)


# ---------------------------------------------------------------------------
# Proxy behavior tests
# ---------------------------------------------------------------------------


class TestProxyBehavior:
    """Test proxy routing logic with mocked backends."""

    def test_proxy_passes_request_to_correct_service(self, client, auth_headers):
        """When a backend service is unreachable, gateway returns 502."""
        response = client.post(
            "/mcp_gateway/v1/inspect_call",
            headers={**auth_headers, "Content-Type": "application/json"},
            json={"name": "read_file", "server_id": "github", "arguments": {}},
        )
        assert response.status_code in (502, 504)

    def test_multiple_path_segments_preserved(self, client, auth_headers):
        """Path after service name is forwarded correctly."""
        response = client.get("/mcp_gateway/v1/health", headers=auth_headers)
        assert response.status_code in (502, 504)

    def test_proxy_uses_explicit_header_allowlist_and_gateway_identity(
        self, client, gateway, auth_headers
    ):
        """Caller-controlled Authorization/Cookie headers never cross the trust boundary."""
        fake_response = SimpleNamespace(
            status_code=200,
            headers={"content-type": "application/json"},
            json=lambda: {"ok": True},
            text="{\"ok\":true}",
        )
        mock_request = AsyncMock(return_value=fake_response)
        with patch.object(gateway.app.state.http_client, "request", mock_request):
            response = client.post(
                "/mcp_gateway/v1/inspect_call",
                headers={
                    **auth_headers,
                    "Authorization": "Bearer caller-controlled",
                    "Cookie": "session=caller-controlled",
                    "Content-Type": "application/json",
                    "X-Request-Id": "req-123",
                },
                json={"name": "read_file", "server_id": "github", "arguments": {}},
            )

        assert response.status_code == 200
        forwarded = mock_request.call_args.kwargs["headers"]
        assert forwarded["X-API-Key"] == "mcp-gateway-service-key-at-least-32-characters"
        assert forwarded["content-type"] == "application/json"
        assert forwarded["x-request-id"] == "req-123"
        assert "authorization" not in forwarded
        assert "cookie" not in forwarded



    def test_oversized_proxy_body_rejected_before_upstream(self, client, auth_headers, gateway):
        body = b"A" * (gateway.MAX_PROXY_BODY_BYTES + 1)
        response = client.post(
            "/mcp_gateway/v1/inspect_call",
            headers={**auth_headers, "Content-Type": "application/octet-stream"},
            content=body,
        )
        assert response.status_code == 413

    def test_forwarded_header_allowlist_excludes_security_sensitive_headers(self, gateway):
        """The static allowlist documents and enforces a deny-by-construction boundary."""
        assert "authorization" not in gateway.FORWARDED_REQUEST_HEADERS
        assert "cookie" not in gateway.FORWARDED_REQUEST_HEADERS
        assert "x-api-key" not in gateway.FORWARDED_REQUEST_HEADERS
        assert "content-type" in gateway.FORWARDED_REQUEST_HEADERS
        assert "x-request-id" in gateway.FORWARDED_REQUEST_HEADERS


# ---------------------------------------------------------------------------
# Async client tests (pytest-asyncio)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_async(app):
    """Verify health endpoint works with httpx AsyncClient."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_auth_rejection_async(app):
    """Verify invalid API key is rejected via async client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/status", headers={"X-API-Key": "bad-key-not-valid"}
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_status_with_valid_key_async(app):
    """Verify authenticated status endpoint via async client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/status", headers={"X-API-Key": VALID_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        assert "services" in data


# ---------------------------------------------------------------------------
# Correlation endpoint tests
# ---------------------------------------------------------------------------


class TestCorrelateEndpoint:
    """/correlate fans out to every service /scan and aggregates findings."""

    def _mock_scan(self, per_service_findings):
        """Build an AsyncMock http-client .post that returns per-service findings.

        `per_service_findings` maps a service base-url substring -> findings list.
        """

        def _post(url, **kwargs):
            findings = []
            for key, val in per_service_findings.items():
                if key in url:
                    findings = val
                    break
            return SimpleNamespace(
                status_code=200,
                headers={"content-type": "application/json"},
                json=lambda f=findings: {"source": "svc", "finding_count": len(f), "findings": f},
            )

        return AsyncMock(side_effect=_post)

    def test_correlate_requires_auth(self, client):
        assert client.post("/correlate", json={"content": "x"}).status_code == 401

    def test_correlate_rejects_empty_content(self, client, auth_headers):
        assert (
            client.post("/correlate", json={"content": ""}, headers=auth_headers).status_code
            == 422
        )

    def test_correlate_aggregates_and_dedupes(self, client, gateway, auth_headers):
        shared = {
            "rule_id": "T1059.001",
            "technique": "Command and Scripting Interpreter T1059",
            "title": "Command and Scripting Interpreter T1059",
            "severity": "high",
            "source": "dataset_poison",
            "evidence": ["powershell"],
        }
        unique = {
            "rule_id": "T1566",
            "technique": "Phishing T1566",
            "title": "Phishing T1566",
            "severity": "medium",
            "source": "llm_redteam",
            "evidence": ["phishing"],
        }
        # Two services report the SAME finding; one reports an extra unique one.
        mock_post = self._mock_scan(
            {
                "mcp-gateway": [dict(shared, source="mcp_gateway")],
                "llm-redteam": [dict(shared, source="llm_redteam"), unique],
                "dataset-poison": [dict(shared, source="dataset_poison")],
                "model-privacy": [],
            }
        )
        with patch.object(gateway.app.state.http_client, "post", mock_post):
            resp = client.post(
                "/correlate",
                json={"content": "powershell.exe -enc; phishing"},
                headers=auth_headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        # shared finding merged into ONE entry; unique stays separate => 2 total.
        assert data["correlated_finding_count"] == 2
        assert data["services_queried"] == 4
        top = data["findings"][0]  # highest severity first
        assert top["rule_id"] == "T1059.001"
        # merged finding observed by all three reporting services.
        assert sorted(set(top["observed_by"])) == ["dataset_poison", "llm_redteam", "mcp_gateway"]

    def test_correlate_partial_result_on_unavailable_service(
        self, client, gateway, auth_headers
    ):
        import httpx as _httpx

        def _post(url, **kwargs):
            if "model-privacy" in url:
                raise _httpx.ConnectError("down")
            return SimpleNamespace(
                status_code=200,
                headers={"content-type": "application/json"},
                json=lambda: {"source": "svc", "finding_count": 0, "findings": []},
            )

        with patch.object(gateway.app.state.http_client, "post", AsyncMock(side_effect=_post)):
            resp = client.post(
                "/correlate", json={"content": "benign"}, headers=auth_headers
            )
        assert resp.status_code == 200
        assert resp.json()["service_status"]["model_privacy"] == "unavailable"
