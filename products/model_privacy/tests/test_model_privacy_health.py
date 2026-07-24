"""Health check test for model_privacy product."""
import os
os.environ.setdefault("MLSEC_API_KEY", "test-key-ci")

from fastapi.testclient import TestClient
from products.model_privacy.server import app

client = TestClient(app)


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["product"] == "model_privacy"