"""Health check test for dataset_poison product."""
import os
os.environ.setdefault("MLSEC_API_KEY", "test-key-ci")

from fastapi.testclient import TestClient
from products.dataset_poison.server import app

client = TestClient(app)


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["product"] == "dataset_poison"