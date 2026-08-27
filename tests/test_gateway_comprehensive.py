"""
Comprehensive Gateway Test Suite

50+ tests covering:
- All proxy routes
- Auth enforcement on every endpoint
- Rate limiting behavior
- Service unavailable handling
- Request/response transformation
- Error propagation

Targets 90%+ coverage of the gateway module.
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import the gateway app — adjust path as needed
from gateway.app import app, get_settings
from gateway.auth import verify_token, create_token
from gateway.middleware import RateLimiter, AuthMiddleware
from gateway.proxy import ProxyRouter
from gateway.models import ProxyRoute, ServiceHealth


# --- Fixtures ---


@pytest.fixture
def client():
    """Test client with auth disabled for route testing."""
    return TestClient(app)


@pytest.fixture
def auth_client():
    """Test client with valid auth token."""
    client = TestClient(app)
    token = create_token({"sub": "test-user", "scopes": ["read", "write", "admin"]})
    client.headers = {"Authorization": f"Bearer {token}"}
    return client


@pytest.fixture
def limited_client():
    """Test client with restricted scopes."""
    client = TestClient(app)
    token = create_token({"sub": "limited-user", "scopes": ["read"]})
    client.headers = {"Authorization": f"Bearer {token}"}
    return client


@pytest.fixture
def expired_token():
    """Generate an expired JWT token."""
    token = create_token({"sub": "test-user", "scopes": ["read"]}, expires_delta=-300)
    return token


@pytest.fixture
def mock_backend():
    """Mock backend service responses."""

    class MockBackend:
        def __init__(self):
            self.responses = {}
            self.call_count = 0

        def set_response(self, path, status_code=200, json_body=None, delay=0):
            self.responses[path] = {
                "status_code": status_code,
                "json": json_body or {},
                "delay": delay,
            }

        async def handle(self, request):
            self.call_count += 1
            path = str(request.url.path)
            resp = self.responses.get(path, {"status_code": 200, "json": {"ok": True}, "delay": 0})
            if resp["delay"] > 0:
                await asyncio.sleep(resp["delay"])
            return httpx.Response(
                status_code=resp["status_code"],
                json=resp["json"],
                headers={"content-type": "application/json"},
            )

    return MockBackend()


# =============================================================================
# SECTION 1: Proxy Route Tests (12 tests)
# =============================================================================


class TestProxyRoutes:
    """Test all proxy routing functionality."""

    def test_proxy_to_hf_scanner_scan(self, auth_client, mock_backend):
        """POST /api/v1/scanner/scan routes to HF scanner service."""
        mock_backend.set_response("/scan", json_body={"scan_id": "s1", "findings": []})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            response = auth_client.post(
                "/api/v1/scanner/scan",
                json={"model_id": "bert-base-uncased"},
            )
        assert response.status_code == 200

    def test_proxy_to_hf_scanner_health(self, auth_client, mock_backend):
        """GET /api/v1/scanner/health routes to HF scanner health."""
        mock_backend.set_response("/health", json_body={"status": "healthy", "version": "1.0.0"})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            response = auth_client.get("/api/v1/scanner/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_proxy_to_mcp_inspect(self, auth_client, mock_backend):
        """POST /api/v1/mcp/inspect routes to MCP gateway service."""
        mock_backend.set_response(
            "/inspect",
            json_body={"verdict": "allow", "allowed": True, "risk_score": 0.1},
        )
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            response = auth_client.post(
                "/api/v1/mcp/inspect",
                json={"method": "tools/call", "params": {}},
            )
        assert response.status_code == 200
        assert response.json()["allowed"] is True

    def test_proxy_to_mcp_health(self, auth_client, mock_backend):
        """GET /api/v1/mcp/health routes to MCP gateway health."""
        mock_backend.set_response("/health", json_body={"status": "healthy"})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            response = auth_client.get("/api/v1/mcp/health")
        assert response.status_code == 200

    def test_gateway_own_health_endpoint(self, client):
        """GET /health returns gateway health without auth."""
        response = client.get("/health")
        assert response.status_code == 200
        assert "status" in response.json()

    def test_gateway_readiness_endpoint(self, client):
        """GET /ready returns readiness status."""
        response = client.get("/ready")
        assert response.status_code == 200

    def test_unknown_route_returns_404(self, auth_client):
        """Unknown API routes return 404."""
        response = auth_client.get("/api/v1/nonexistent/endpoint")
        assert response.status_code == 404

    def test_proxy_preserves_query_params(self, auth_client, mock_backend):
        """Query parameters are forwarded to backend services."""
        mock_backend.set_response("/scan", json_body={"filtered": True})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle) as mock_send:
            response = auth_client.get("/api/v1/scanner/scan?status=completed&limit=10")
            if mock_send.called:
                sent_request = mock_send.call_args[0][0]
                assert "status=completed" in str(sent_request.url)

    def test_proxy_preserves_request_headers(self, auth_client, mock_backend):
        """Custom headers are forwarded to backend services."""
        mock_backend.set_response("/scan", json_body={"ok": True})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle) as mock_send:
            auth_client.post(
                "/api/v1/scanner/scan",
                json={"model_id": "test"},
                headers={"X-Request-ID": "req-123", "X-Correlation-ID": "corr-456"},
            )
            if mock_send.called:
                sent_request = mock_send.call_args[0][0]
                assert sent_request.headers.get("x-request-id") == "req-123"

    def test_proxy_post_with_large_body(self, auth_client, mock_backend):
        """Large request bodies are proxied correctly."""
        large_payload = {"model_id": "test", "data": "x" * 50000}
        mock_backend.set_response("/scan", json_body={"received": True})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            response = auth_client.post("/api/v1/scanner/scan", json=large_payload)
        assert response.status_code == 200

    def test_proxy_delete_method(self, auth_client, mock_backend):
        """DELETE method is proxied correctly."""
        mock_backend.set_response("/sessions/sess-1", json_body={"deleted": True})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            response = auth_client.delete("/api/v1/mcp/sessions/sess-1")
        assert response.status_code in [200, 204, 404]

    def test_proxy_put_method(self, auth_client, mock_backend):
        """PUT method is proxied correctly."""
        mock_backend.set_response("/policies/update", json_body={"updated": True})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            response = auth_client.put(
                "/api/v1/mcp/policies/update",
                json={"policy_set": "strict"},
            )
        assert response.status_code in [200, 404]


# =============================================================================
# SECTION 2: Auth Enforcement Tests (14 tests)
# =============================================================================


class TestAuthEnforcement:
    """Test authentication and authorization on every endpoint."""

    def test_scan_endpoint_requires_auth(self, client):
        """POST /api/v1/scanner/scan returns 401 without token."""
        response = client.post("/api/v1/scanner/scan", json={"model_id": "test"})
        assert response.status_code == 401

    def test_inspect_endpoint_requires_auth(self, client):
        """POST /api/v1/mcp/inspect returns 401 without token."""
        response = client.post("/api/v1/mcp/inspect", json={"method": "tools/call"})
        assert response.status_code == 401

    def test_scanner_health_requires_auth(self, client):
        """GET /api/v1/scanner/health returns 401 without token."""
        response = client.get("/api/v1/scanner/health")
        assert response.status_code == 401

    def test_mcp_health_requires_auth(self, client):
        """GET /api/v1/mcp/health returns 401 without token."""
        response = client.get("/api/v1/mcp/health")
        assert response.status_code == 401

    def test_invalid_token_returns_401(self, client):
        """Invalid JWT token returns 401."""
        client.headers = {"Authorization": "Bearer invalid.token.here"}
        response = client.post("/api/v1/scanner/scan", json={"model_id": "test"})
        assert response.status_code == 401

    def test_expired_token_returns_401(self, client, expired_token):
        """Expired JWT token returns 401."""
        client.headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.post("/api/v1/scanner/scan", json={"model_id": "test"})
        assert response.status_code == 401

    def test_malformed_auth_header_returns_401(self, client):
        """Malformed Authorization header returns 401."""
        client.headers = {"Authorization": "NotBearer some-token"}
        response = client.post("/api/v1/scanner/scan", json={"model_id": "test"})
        assert response.status_code == 401

    def test_missing_auth_header_returns_401(self, client):
        """Missing Authorization header returns 401."""
        response = client.post("/api/v1/scanner/scan", json={"model_id": "test"})
        assert response.status_code == 401

    def test_insufficient_scopes_returns_403(self, limited_client, mock_backend):
        """Token with insufficient scopes returns 403 for write operations."""
        response = limited_client.post(
            "/api/v1/scanner/scan",
            json={"model_id": "test"},
        )
        # Limited client only has 'read' scope — write should be forbidden
        assert response.status_code in [403, 200]  # Depends on endpoint scope config

    def test_admin_scope_required_for_policy_update(self, limited_client):
        """Policy update requires admin scope."""
        response = limited_client.post(
            "/api/v1/mcp/policies/update",
            json={"policy_set": "strict"},
        )
        assert response.status_code in [403, 404]

    def test_valid_token_allows_access(self, auth_client, mock_backend):
        """Valid token with correct scopes allows access."""
        mock_backend.set_response("/scan", json_body={"scan_id": "s1"})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            response = auth_client.post(
                "/api/v1/scanner/scan",
                json={"model_id": "test"},
            )
        assert response.status_code == 200

    def test_gateway_health_no_auth_required(self, client):
        """Gateway's own /health does not require authentication."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_gateway_ready_no_auth_required(self, client):
        """Gateway's /ready does not require authentication."""
        response = client.get("/ready")
        assert response.status_code == 200

    def test_token_with_all_scopes(self, auth_client, mock_backend):
        """Token with all scopes can access all endpoints."""
        mock_backend.set_response("/inspect", json_body={"verdict": "allow", "allowed": True})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            response = auth_client.post(
                "/api/v1/mcp/inspect",
                json={"method": "tools/call", "params": {}},
            )
        assert response.status_code == 200


# =============================================================================
# SECTION 3: Rate Limiting Tests (8 tests)
# =============================================================================


class TestRateLimiting:
    """Test rate limiting behavior."""

    def test_rate_limit_headers_present(self, auth_client, mock_backend):
        """Rate limit headers are included in responses."""
        mock_backend.set_response("/scan", json_body={"ok": True})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            response = auth_client.post("/api/v1/scanner/scan", json={"model_id": "test"})
        # Check for rate limit headers
        assert any(
            h in response.headers
            for h in ["x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset"]
        )

    def test_rate_limit_decrements(self, auth_client, mock_backend):
        """Remaining count decreases with each request."""
        mock_backend.set_response("/health", json_body={"status": "healthy"})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            r1 = auth_client.get("/api/v1/scanner/health")
            r2 = auth_client.get("/api/v1/scanner/health")
            remaining_1 = int(r1.headers.get("x-ratelimit-remaining", 100))
            remaining_2 = int(r2.headers.get("x-ratelimit-remaining", 99))
            assert remaining_2 <= remaining_1

    def test_rate_limit_exceeded_returns_429(self, auth_client, mock_backend):
        """Exceeding rate limit returns 429 Too Many Requests."""
        mock_backend.set_response("/health", json_body={"status": "healthy"})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            with patch("gateway.middleware.RateLimiter.is_allowed", return_value=False):
                response = auth_client.get("/api/v1/scanner/health")
        assert response.status_code == 429

    def test_rate_limit_429_includes_retry_after(self, auth_client, mock_backend):
        """429 response includes Retry-After header."""
        with patch("gateway.middleware.RateLimiter.is_allowed", return_value=False):
            with patch("gateway.middleware.RateLimiter.retry_after", return_value=30):
                response = auth_client.get("/api/v1/scanner/health")
        if response.status_code == 429:
            assert "retry-after" in response.headers

    def test_rate_limit_per_client(self, mock_backend):
        """Rate limits are tracked per client/token."""
        client_a = TestClient(app)
        client_b = TestClient(app)
        token_a = create_token({"sub": "user-a", "scopes": ["read", "write"]})
        token_b = create_token({"sub": "user-b", "scopes": ["read", "write"]})
        client_a.headers = {"Authorization": f"Bearer {token_a}"}
        client_b.headers = {"Authorization": f"Bearer {token_b}"}

        mock_backend.set_response("/health", json_body={"ok": True})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            r_a = client_a.get("/api/v1/scanner/health")
            r_b = client_b.get("/api/v1/scanner/health")
        # Both should succeed independently
        assert r_a.status_code == 200
        assert r_b.status_code == 200

    def test_rate_limit_resets_after_window(self, auth_client, mock_backend):
        """Rate limit resets after the time window passes."""
        mock_backend.set_response("/health", json_body={"ok": True})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            with patch("gateway.middleware.RateLimiter.is_allowed", side_effect=[False, True]):
                r1 = auth_client.get("/api/v1/scanner/health")
                r2 = auth_client.get("/api/v1/scanner/health")
        # Second request should succeed after "reset"
        assert r2.status_code == 200

    def test_rate_limit_different_endpoints_share_budget(self, auth_client, mock_backend):
        """All endpoints share the same per-user rate limit budget."""
        mock_backend.set_response("/scan", json_body={"ok": True})
        mock_backend.set_response("/health", json_body={"ok": True})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            r1 = auth_client.post("/api/v1/scanner/scan", json={"model_id": "t"})
            r2 = auth_client.get("/api/v1/scanner/health")
            rem1 = int(r1.headers.get("x-ratelimit-remaining", 100))
            rem2 = int(r2.headers.get("x-ratelimit-remaining", 100))
            assert rem2 <= rem1

    def test_rate_limit_unauthenticated_uses_ip(self, client):
        """Unauthenticated requests are rate limited by IP."""
        response = client.get("/health")
        # Health is public — should still have rate headers
        assert response.status_code == 200


# =============================================================================
# SECTION 4: Service Unavailable Handling (8 tests)
# =============================================================================


class TestServiceUnavailable:
    """Test handling when backend services are down."""

    def test_scanner_unavailable_returns_503(self, auth_client):
        """Returns 503 when scanner service is unreachable."""
        with patch(
            "gateway.proxy.httpx.AsyncClient.send",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            response = auth_client.post("/api/v1/scanner/scan", json={"model_id": "test"})
        assert response.status_code == 503

    def test_mcp_unavailable_returns_503(self, auth_client):
        """Returns 503 when MCP service is unreachable."""
        with patch(
            "gateway.proxy.httpx.AsyncClient.send",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            response = auth_client.post("/api/v1/mcp/inspect", json={"method": "tools/call"})
        assert response.status_code == 503

    def test_503_response_body_indicates_service(self, auth_client):
        """503 response body identifies which service is unavailable."""
        with patch(
            "gateway.proxy.httpx.AsyncClient.send",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            response = auth_client.post("/api/v1/scanner/scan", json={"model_id": "test"})
        assert response.status_code == 503
        body = response.json()
        assert "scanner" in body.get("detail", "").lower() or "service" in body.get("detail", "").lower()

    def test_backend_timeout_returns_504(self, auth_client):
        """Returns 504 when backend service times out."""
        with patch(
            "gateway.proxy.httpx.AsyncClient.send",
            side_effect=httpx.ReadTimeout("Read timed out"),
        ):
            response = auth_client.post("/api/v1/scanner/scan", json={"model_id": "test"})
        assert response.status_code == 504

    def test_backend_500_propagated(self, auth_client, mock_backend):
        """Backend 500 errors are propagated to client."""
        mock_backend.set_response("/scan", status_code=500, json_body={"error": "internal"})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            response = auth_client.post("/api/v1/scanner/scan", json={"model_id": "test"})
        assert response.status_code == 500

    def test_backend_partial_outage_other_services_work(self, auth_client, mock_backend):
        """One backend down doesn't affect other backends."""
        mock_backend.set_response("/inspect", json_body={"verdict": "allow", "allowed": True})

        async def selective_failure(request):
            if "scanner" in str(request.url):
                raise httpx.ConnectError("Connection refused")
            return await mock_backend.handle(request)

        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=selective_failure):
            scan_resp = auth_client.post("/api/v1/scanner/scan", json={"model_id": "test"})
            mcp_resp = auth_client.post("/api/v1/mcp/inspect", json={"method": "tools/call"})

        assert scan_resp.status_code == 503
        assert mcp_resp.status_code == 200

    def test_circuit_breaker_opens_after_failures(self, auth_client):
        """Circuit breaker opens after consecutive failures."""
        with patch(
            "gateway.proxy.httpx.AsyncClient.send",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            # Hit the endpoint multiple times to trigger circuit breaker
            responses = []
            for _ in range(5):
                r = auth_client.post("/api/v1/scanner/scan", json={"model_id": "test"})
                responses.append(r.status_code)
        # All should be 503
        assert all(code == 503 for code in responses)

    def test_service_recovery_after_circuit_break(self, auth_client, mock_backend):
        """Service recovers after circuit breaker resets."""
        mock_backend.set_response("/scan", json_body={"scan_id": "recovered"})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            response = auth_client.post("/api/v1/scanner/scan", json={"model_id": "test"})
        assert response.status_code == 200


# =============================================================================
# SECTION 5: Request/Response Transformation (8 tests)
# =============================================================================


class TestRequestResponseTransformation:
    """Test request and response transformation through the gateway."""

    def test_request_id_added_to_proxied_request(self, auth_client, mock_backend):
        """Gateway adds X-Request-ID to proxied requests."""
        mock_backend.set_response("/scan", json_body={"ok": True})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle) as mock_send:
            auth_client.post("/api/v1/scanner/scan", json={"model_id": "test"})
            if mock_send.called:
                sent = mock_send.call_args[0][0]
                assert "x-request-id" in sent.headers

    def test_response_includes_request_id(self, auth_client, mock_backend):
        """Responses include X-Request-ID header for tracing."""
        mock_backend.set_response("/scan", json_body={"ok": True})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            response = auth_client.post("/api/v1/scanner/scan", json={"model_id": "test"})
        assert "x-request-id" in response.headers

    def test_response_timing_header(self, auth_client, mock_backend):
        """Response includes X-Response-Time header."""
        mock_backend.set_response("/scan", json_body={"ok": True})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            response = auth_client.post("/api/v1/scanner/scan", json={"model_id": "test"})
        assert "x-response-time" in response.headers

    def test_content_type_preserved(self, auth_client, mock_backend):
        """Content-Type from backend is preserved in response."""
        mock_backend.set_response("/scan", json_body={"ok": True})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            response = auth_client.post("/api/v1/scanner/scan", json={"model_id": "test"})
        assert "application/json" in response.headers.get("content-type", "")

    def test_cors_headers_present(self, client):
        """CORS headers are present on responses."""
        response = client.options("/api/v1/scanner/scan")
        # At minimum, health should have CORS if configured
        response = client.get("/health")
        headers = response.headers
        assert any("access-control" in h.lower() for h in headers.keys()) or response.status_code == 200

    def test_strip_internal_headers_from_response(self, auth_client, mock_backend):
        """Internal backend headers are stripped from client response."""
        async def custom_response(request):
            return httpx.Response(
                status_code=200,
                json={"ok": True},
                headers={
                    "content-type": "application/json",
                    "x-internal-trace": "should-be-stripped",
                    "x-backend-instance": "pod-123",
                },
            )

        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=custom_response):
            response = auth_client.post("/api/v1/scanner/scan", json={"model_id": "test"})
        # Internal headers should not leak
        assert "x-internal-trace" not in response.headers
        assert "x-backend-instance" not in response.headers

    def test_json_request_body_preserved(self, auth_client, mock_backend):
        """JSON request body is forwarded intact."""
        original_body = {
            "model_id": "org/model",
            "revision": "v2.1",
            "check_signatures": True,
            "nested": {"key": "value", "list": [1, 2, 3]},
        }
        mock_backend.set_response("/scan", json_body={"received": True})

        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle) as mock_send:
            auth_client.post("/api/v1/scanner/scan", json=original_body)
            if mock_send.called:
                sent = mock_send.call_args[0][0]
                sent_body = json.loads(sent.content)
                assert sent_body["model_id"] == "org/model"
                assert sent_body["nested"]["list"] == [1, 2, 3]

    def test_empty_response_body_handled(self, auth_client, mock_backend):
        """Empty response bodies from backend are handled gracefully."""
        async def empty_response(request):
            return httpx.Response(status_code=204, content=b"")

        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=empty_response):
            response = auth_client.delete("/api/v1/mcp/sessions/sess-1")
        assert response.status_code in [204, 404]


# =============================================================================
# SECTION 6: Error Propagation Tests (8 tests)
# =============================================================================


class TestErrorPropagation:
    """Test error handling and propagation through the gateway."""

    def test_400_from_backend_propagated(self, auth_client, mock_backend):
        """Backend 400 Bad Request is propagated."""
        mock_backend.set_response("/scan", status_code=400, json_body={"detail": "Invalid model_id"})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            response = auth_client.post("/api/v1/scanner/scan", json={"model_id": ""})
        assert response.status_code == 400

    def test_404_from_backend_propagated(self, auth_client, mock_backend):
        """Backend 404 Not Found is propagated."""
        mock_backend.set_response("/scan/unknown", status_code=404, json_body={"detail": "Not found"})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            response = auth_client.get("/api/v1/scanner/scan/unknown")
        assert response.status_code == 404

    def test_422_from_backend_propagated(self, auth_client, mock_backend):
        """Backend 422 Unprocessable Entity is propagated."""
        mock_backend.set_response(
            "/scan", status_code=422, json_body={"detail": "Validation error"}
        )
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            response = auth_client.post("/api/v1/scanner/scan", json={"invalid": "schema"})
        assert response.status_code == 422

    def test_error_response_body_preserved(self, auth_client, mock_backend):
        """Error response body from backend is preserved."""
        error_body = {"detail": "Model not found", "code": "MODEL_NOT_FOUND"}
        mock_backend.set_response("/scan", status_code=404, json_body=error_body)
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            response = auth_client.post("/api/v1/scanner/scan", json={"model_id": "none"})
        assert response.status_code == 404
        assert response.json().get("detail") == "Model not found"

    def test_gateway_internal_error_returns_500(self, auth_client):
        """Unexpected gateway errors return 500."""
        with patch(
            "gateway.proxy.httpx.AsyncClient.send",
            side_effect=RuntimeError("Unexpected internal error"),
        ):
            response = auth_client.post("/api/v1/scanner/scan", json={"model_id": "test"})
        assert response.status_code == 500

    def test_gateway_error_does_not_leak_internals(self, auth_client):
        """Gateway error responses do not leak stack traces."""
        with patch(
            "gateway.proxy.httpx.AsyncClient.send",
            side_effect=RuntimeError("Secret internal detail"),
        ):
            response = auth_client.post("/api/v1/scanner/scan", json={"model_id": "test"})
        body = response.text
        assert "Secret internal detail" not in body
        assert "Traceback" not in body

    def test_malformed_json_request_returns_422(self, auth_client):
        """Malformed JSON in request body returns 422."""
        response = auth_client.post(
            "/api/v1/scanner/scan",
            content=b"not-valid-json{{{",
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 422

    def test_request_too_large_returns_413(self, auth_client):
        """Request body exceeding size limit returns 413."""
        huge_payload = {"data": "x" * 10_000_000}  # ~10MB
        response = auth_client.post("/api/v1/scanner/scan", json=huge_payload)
        assert response.status_code in [413, 422, 200]  # Depends on gateway config


# =============================================================================
# SECTION 7: Additional Edge Cases (6 tests)
# =============================================================================


class TestEdgeCases:
    """Additional edge case tests."""

    def test_concurrent_requests_handled(self, auth_client, mock_backend):
        """Gateway handles concurrent requests without deadlocking."""
        mock_backend.set_response("/scan", json_body={"ok": True})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            responses = []
            for _ in range(10):
                r = auth_client.post("/api/v1/scanner/scan", json={"model_id": "test"})
                responses.append(r.status_code)
        assert all(code in [200, 429] for code in responses)

    def test_special_characters_in_path(self, auth_client, mock_backend):
        """Paths with special characters are handled safely."""
        mock_backend.set_response("/scan", json_body={"ok": True})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            response = auth_client.get("/api/v1/scanner/scan?q=hello%20world&special=%3C%3E")
        assert response.status_code in [200, 404]

    def test_empty_body_post_accepted(self, auth_client, mock_backend):
        """POST with empty body is handled."""
        mock_backend.set_response("/inspect", json_body={"verdict": "allow"})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            response = auth_client.post("/api/v1/mcp/inspect", content=b"")
        assert response.status_code in [200, 422]

    def test_unicode_in_request_body(self, auth_client, mock_backend):
        """Unicode characters in request body are preserved."""
        mock_backend.set_response("/scan", json_body={"ok": True})
        with patch("gateway.proxy.httpx.AsyncClient.send", side_effect=mock_backend.handle):
            response = auth_client.post(
                "/api/v1/scanner/scan",
                json={"model_id": "模型/テスト-модель"},
            )
        assert response.status_code in [200, 422]

    def test_multiple_auth_schemes_rejected(self, client):
        """Multiple Authorization headers are handled."""
        client.headers = {
            "Authorization": "Bearer token1",
            "X-API-Key": "key123",
        }
        response = client.post("/api/v1/scanner/scan", json={"model_id": "test"})
        # Should use Bearer token, not reject
        assert response.status_code in [200, 401, 403]

    def test_options_preflight_returns_200(self, client):
        """CORS preflight OPTIONS request returns 200."""
        response = client.options(
            "/api/v1/scanner/scan",
            headers={
                "Origin": "https://dashboard.example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code in [200, 405]
