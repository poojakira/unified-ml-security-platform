"""Self-contained health checks for the architecture gateway."""

from __future__ import annotations

import importlib
import os

from fastapi.testclient import TestClient

EXPECTED_SERVICES = {
    "hf_scanner",
    "mcp_gateway",
    "adv_ml",
    "llm_redteam",
    "dataset_poison",
    "model_privacy",
    "pulsenet",
}


def test_gateway_health_endpoint_exposes_expected_services(monkeypatch) -> None:
    """The health response comes from this gateway, not an arbitrary local port."""
    monkeypatch.setenv("API_KEY", "test-key-for-health-check-only-123456")
    gateway = importlib.import_module("gateway_server")
    gateway = importlib.reload(gateway)

    with TestClient(gateway.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert set(payload["services"]) == EXPECTED_SERVICES

    os.environ.pop("API_KEY", None)
