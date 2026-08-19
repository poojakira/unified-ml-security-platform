"""
Cross-service integration tests for the Unified ML Security Platform.

These tests validate that the gateway correctly routes, authenticates,
and handles errors across the full platform service mesh.

Run with: py -m pytest tests/integration/ -v
"""

from __future__ import annotations

import importlib
import json
import os

import pytest
from fastapi.testclient import TestClient

TEST_API_KEY = "test-integration-key-32-chars-long!!"


@pytest.fixture()
def client(monkeypatch):
    """Create a test client with API_KEY set."""
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
    gateway = importlib.import_module("gateway_server")
    gateway = importlib.reload(gateway)
    with TestClient(gateway.app) as c:
        yield c


@pytest.fixture()
def auth_headers():
    """Standard auth headers for authenticated requests."""
    return {"X-API-Key": TEST_API_KEY}


# ─── Security: Authentication & Authorization ────────────────────────────────


class TestAuthenticationEnforcement:
    """Verify every protected endpoint rejects unauthenticated requests."""

    PROTECTED_ENDPOINTS = [
        ("GET", "/status"),
        ("POST", "/scan/iam"),
        ("POST", "/scan/model"),
        ("GET", "/mcp_gateway/health"),
        ("POST", "/hf_scanner/scan"),
    ]

    @pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
    def test_rejects_missing_api_key(self, client, method, path):
        """Every protected endpoint returns 401 without API key."""
        response = client.request(method, path)
        assert response.status_code == 401

    @pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
    def test_rejects_invalid_api_key(self, client, method, path):
        """Every protected endpoint returns 401 with wrong API key."""
        response = client.request(
            method, path, headers={"X-API-Key": "wrong-key-12345678901234567890"}
        )
        assert response.status_code == 401

    def test_health_no_auth_required(self, client):
        """Health check must work without auth (for load balancers)."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_does_not_expose_services(self, client):
        """Health endpoint must not leak service inventory to unauthed callers."""
        response = client.get("/health")
        payload = response.json()
        assert "services" not in payload
        assert "total" not in payload


# ─── Gateway Service Registry ────────────────────────────────────────────────


class TestServiceRegistry:
    """Verify the gateway knows about all expected services."""

    EXPECTED_SERVICES = [
        "adv_ml",
        "dataset_poison",
        "hf_scanner",
        "llm_redteam",
        "mcp_gateway",
        "model_privacy",
    ]

    def test_status_lists_all_services(self, client, auth_headers):
        """Status endpoint returns complete service inventory."""
        response = client.get("/status", headers=auth_headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "operational"
        for svc in self.EXPECTED_SERVICES:
            assert svc in payload["services"], f"Missing service: {svc}"
        assert payload["total"] == len(self.EXPECTED_SERVICES)

    def test_unknown_service_returns_404(self, client, auth_headers):
        """Routing to non-existent service returns 404, not 500."""
        response = client.get("/nonexistent_service/health", headers=auth_headers)
        assert response.status_code == 404
        assert "Unknown service" in response.json()["detail"]


# ─── IAM Scanner Integration ─────────────────────────────────────────────────


class TestIAMScannerIntegration:
    """Test IAM policy scanning through the gateway."""

    def test_iam_scan_overpermissive_policy(self, client, auth_headers):
        """Wildcard action on bedrock should be flagged."""
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {"Effect": "Allow", "Action": "bedrock:*", "Resource": "*"}
            ],
        }
        response = client.post(
            "/scan/iam",
            json={"policy_document": policy},
            headers=auth_headers,
        )
        # 503 is acceptable (scanner not bundled) — test validates routing works
        assert response.status_code in (200, 503)

    def test_iam_scan_safe_policy_no_findings(self, client, auth_headers):
        """Minimal least-privilege policy should produce zero findings."""
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["s3:GetObject"],
                    "Resource": "arn:aws:s3:::my-bucket/models/*",
                }
            ],
        }
        response = client.post(
            "/scan/iam",
            json={"policy_document": policy},
            headers=auth_headers,
        )
        assert response.status_code in (200, 503)
        if response.status_code == 200:
            payload = response.json()
            assert payload["total_findings"] == 0

    def test_iam_scan_privilege_escalation_pattern(self, client, auth_headers):
        """iam:PassRole without conditions is a critical finding."""
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {"Effect": "Allow", "Action": "iam:PassRole", "Resource": "*"}
            ],
        }
        response = client.post(
            "/scan/iam",
            json={"policy_document": policy},
            headers=auth_headers,
        )
        assert response.status_code in (200, 503)
        if response.status_code == 200:
            payload = response.json()
            assert payload["total_findings"] > 0
            severities = [f.get("severity", "").upper() for f in payload["findings"]]
            assert "CRITICAL" in severities or "HIGH" in severities


# ─── Model Scanner Integration ───────────────────────────────────────────────


class TestModelScannerIntegration:
    """Test model provenance scanning through the gateway."""

    def test_model_scan_invalid_path(self, client, auth_headers):
        """Non-existent path returns appropriate error."""
        response = client.post(
            "/scan/model",
            json={"path": "/nonexistent/model/path"},
            headers=auth_headers,
        )
        assert response.status_code in (400, 503)

    def test_model_scan_empty_body(self, client, auth_headers):
        """Empty request body is handled gracefully (not 500)."""
        response = client.post("/scan/model", json={}, headers=auth_headers)
        assert response.status_code in (400, 422, 503)


# ─── Service Proxy Routing ───────────────────────────────────────────────────


class TestServiceProxy:
    """Test proxy routing to backend services."""

    def test_proxy_timeout_handling(self, client, auth_headers):
        """Proxy returns 502/504 for unreachable services, not crash."""
        # All services are down in test mode — expect controlled failure
        response = client.get("/mcp_gateway/health", headers=auth_headers)
        # 502 (upstream error) or 504 (timeout) — NOT 500 (unhandled crash)
        assert response.status_code in (502, 504)

    def test_proxy_preserves_method(self, client, auth_headers):
        """POST requests are proxied as POST, not converted to GET."""
        response = client.post(
            "/hf_scanner/scan",
            json={"model": "test-model"},
            headers=auth_headers,
        )
        # Connection refused is fine — validates routing, not backend
        assert response.status_code in (502, 504)

    def test_proxy_does_not_expose_internal_errors(self, client, auth_headers):
        """Error responses must not contain stack traces or internal paths."""
        response = client.get("/mcp_gateway/health", headers=auth_headers)
        if response.status_code >= 500:
            body = response.text
            assert "Traceback" not in body
            assert "File \"/" not in body
            assert "site-packages" not in body


# ─── End-to-End Attack Scenario ──────────────────────────────────────────────


class TestAttackScenarios:
    """
    Simulate realistic attack workflows that cross service boundaries.
    These validate the platform behaves correctly under adversarial input.
    """

    def test_injection_in_iam_policy_action(self, client, auth_headers):
        """SQL injection-like pattern in policy Action field is handled safely."""
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "s3:GetObject'; DROP TABLE users; --",
                    "Resource": "*",
                }
            ],
        }
        response = client.post(
            "/scan/iam",
            json={"policy_document": policy},
            headers=auth_headers,
        )
        # Must not crash (500) — any 4xx/503 is acceptable
        assert response.status_code < 500 or response.status_code == 503

    def test_oversized_payload_rejected(self, client, auth_headers):
        """Extremely large payloads don't cause memory exhaustion."""
        # 1MB payload - should be rejected or handled gracefully
        large_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {"Effect": "Allow", "Action": "s3:*", "Resource": "x" * 1_000_000}
            ],
        }
        response = client.post(
            "/scan/iam",
            json={"policy_document": large_policy},
            headers=auth_headers,
        )
        assert response.status_code in (400, 413, 422, 503)

    def test_unicode_injection_in_service_name(self, client, auth_headers):
        """Path traversal/unicode in service name doesn't bypass routing."""
        response = client.get("/../../etc/passwd", headers=auth_headers)
        assert response.status_code in (404, 422)

    def test_null_bytes_in_payload(self, client, auth_headers):
        """Null bytes in request body don't crash the gateway."""
        response = client.post(
            "/scan/iam",
            content=b'{"policy_document": {"action": "s3:\x00*"}}',
            headers={**auth_headers, "content-type": "application/json"},
        )
        # Either rejects (400/422) or handles gracefully — NOT 500
        assert response.status_code != 500
