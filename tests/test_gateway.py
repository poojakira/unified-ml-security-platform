"""Tests for the unified gateway server.

Covers:
- Health endpoint (unauthenticated)
- API key authentication
- Service routing by path prefix
- Invalid API key rejection
"""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

# Set required env vars BEFORE importing the gateway module
os.environ.setdefault("API_KEY", "test-api-key-that-is-at-least-32-characters-long")

# Patch sys.exit so the gateway module doesn't kill the test process during import
# if API_KEY validation was already handled above, this is belt-and-suspenders.
_original_exit = sys.exit


def _no_exit(code=0):
    raise SystemExit(code)


# Now safe to import gateway
from gateway_server import app, SERVICES, API_KEY  # noqa: E402

from fastapi.testclient import TestClient

VALID_API_KEY = os.environ["API_KEY"]
INVALID_API_KEY = "invalid-key-definitely-wrong-and-short"


@pytest.fixture
def client():
    """Synchronous test client for the gateway."""
    return TestClient(app)


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

    def test_known_services_are_routable(self, client, auth_headers):
        """All configured services should be recognized (not 404).
        They may return 502/504 since backends aren't running, but not 404."""
        for service_name in SERVICES:
            response = client.get(f"/{service_name}/health", headers=auth_headers)
            # Should NOT be 404 (unknown service) or 401 (auth failure)
            assert response.status_code != 404, f"{service_name} returned 404"
            assert response.status_code != 401, f"{service_name} returned 401"

    def test_routing_requires_auth(self, client):
        """Service routes require API key authentication."""
        response = client.get("/hf_scanner/health")
        assert response.status_code == 401

    def test_status_endpoint_lists_services(self, client, auth_headers):
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
            "/hf_scanner/scan",
            headers={**auth_headers, "Content-Type": "application/json"},
            json={"model_id": "test/model"},
        )
        # Backend not running => 502 (upstream error) or 504 (timeout)
        assert response.status_code in (502, 504)

    def test_multiple_path_segments_preserved(self, client, auth_headers):
        """Path after service name is forwarded correctly."""
        response = client.get("/adv_ml/eval/status", headers=auth_headers)
        # Should attempt to reach adv-ml service, not 404
        assert response.status_code in (502, 504)


# ---------------------------------------------------------------------------
# Async client tests (pytest-asyncio)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_async():
    """Verify health endpoint works with httpx AsyncClient."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_auth_rejection_async():
    """Verify invalid API key is rejected via async client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            "/status", headers={"X-API-Key": "bad-key-not-valid"}
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_status_with_valid_key_async():
    """Verify authenticated status endpoint via async client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            "/status", headers={"X-API-Key": VALID_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        assert "services" in data
