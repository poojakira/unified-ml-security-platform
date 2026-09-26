"""Tests for the real (non-stub) dataset_poison /scan endpoint.

These tests force a valid >=32-char MLSEC_API_KEY at request time so they are
independent of test-ordering (sibling health tests set a short placeholder key
via os.environ.setdefault, which must not weaken these assertions).
"""

import os

import pytest
from fastapi.testclient import TestClient

from products.dataset_poison.server import app

VALID_KEY = "dataset-poison-scan-key-at-least-32-characters"
client = TestClient(app)


@pytest.fixture(autouse=True)
def _valid_key(monkeypatch):
    # Override any short key a sibling test set first; auth reads env per request.
    monkeypatch.setenv("MLSEC_API_KEY", VALID_KEY)


def _auth():
    return {"x-api-key": VALID_KEY}


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["product"] == "dataset_poison"


def test_scan_requires_auth() -> None:
    assert client.post("/scan", json={"content": "x"}).status_code == 401


def test_scan_wrong_key_rejected() -> None:
    resp = client.post("/scan", json={"content": "x"}, headers={"x-api-key": "wrong"})
    assert resp.status_code == 401


def test_scan_detects_real_attack_content() -> None:
    resp = client.post(
        "/scan",
        json={"content": "powershell.exe -EncodedCommand ABC; subprocess.call(eval(x))"},
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "dataset_poison"
    assert data["finding_count"] >= 1
    f = data["findings"][0]
    assert f["severity"] in {"critical", "high", "medium", "low", "info"}
    assert f["technique"] is not None
    assert f["evidence"]


def test_scan_benign_content_no_findings() -> None:
    resp = client.post(
        "/scan",
        json={"content": "the quick brown fox jumps over the lazy dog"},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["finding_count"] == 0


def test_scan_rejects_oversized_content() -> None:
    resp = client.post("/scan", json={"content": "A" * 200_001}, headers=_auth())
    assert resp.status_code == 422


def test_scan_fails_closed_when_key_unconfigured(monkeypatch) -> None:
    # A too-short/absent service key must fail closed (503), never allow.
    monkeypatch.setenv("MLSEC_API_KEY", "short")
    resp = client.post("/scan", json={"content": "x"}, headers={"x-api-key": "short"})
    assert resp.status_code == 503
