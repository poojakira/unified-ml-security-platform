"""Health check test for hf_scanner product."""
import os
os.environ.setdefault("MLSEC_API_KEY", "test-key-ci")

from fastapi.testclient import TestClient
from products.hf_scanner.server import app

client = TestClient(app)


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["product"] == "hf_scanner"