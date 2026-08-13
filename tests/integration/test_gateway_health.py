"""Integration tests for the unified gateway."""

from __future__ import annotations

import importlib
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch):
    """Create a test client with API_KEY set."""
    monkeypatch.setenv("API_KEY", "test-key-for-health-check-only-123456")
    gateway = importlib.import_module("gateway_server")
    gateway = importlib.reload(gateway)
    with TestClient(gateway.app) as c:
        yield c


def test_gateway_health_endpoint(client) -> None:
    """Health endpoint works without auth."""
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert "version" in payload


def test_gateway_status_requires_auth(client) -> None:
    """Status endpoint requires API key."""
    response = client.get("/status")
    assert response.status_code == 401


def test_gateway_status_with_auth(client) -> None:
    """Status endpoint returns service availability."""
    response = client.get(
        "/status",
        headers={"X-API-Key": "test-key-for-health-check-only-123456"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "operational"
    assert "services" in payload
    assert "iam_scanner" in payload["services"]
    assert "hf_scanner" in payload["services"]
    assert "adv_ml" in payload["services"]
    assert payload["total"] == 3


def test_scan_iam_requires_auth(client) -> None:
    """IAM scan endpoint requires API key."""
    response = client.post("/scan/iam", json={"policy_document": {}})
    assert response.status_code == 401


def test_scan_iam_with_valid_policy(client) -> None:
    """IAM scan returns findings for an overly permissive policy."""
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "bedrock:*",
                "Resource": "*",
            }
        ],
    }
    response = client.post(
        "/scan/iam",
        json={"policy_document": policy},
        headers={"X-API-Key": "test-key-for-health-check-only-123456"},
    )
    # Should work if aws-agent-identity-guard is installed, 503 if not
    assert response.status_code in (200, 503)
    if response.status_code == 200:
        payload = response.json()
        assert "findings" in payload
        assert "total_findings" in payload
        assert isinstance(payload["findings"], list)


def test_scan_model_requires_auth(client) -> None:
    """Model scan endpoint requires API key."""
    response = client.post("/scan/model", json={"path": "/tmp/test"})
    assert response.status_code == 401


def test_scan_model_bad_path(client) -> None:
    """Model scan rejects nonexistent paths."""
    response = client.post(
        "/scan/model",
        json={"path": "/nonexistent/path/12345"},
        headers={"X-API-Key": "test-key-for-health-check-only-123456"},
    )
    # 400 if scanner available, 503 if not installed
    assert response.status_code in (400, 503)
