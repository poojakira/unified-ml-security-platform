"""Behavior tests for the shared auth/findings contract and every product service.

These exercise the cross-service pieces that the gateway depends on:

* ``products.common.auth`` — constant-time API-key check that fails **closed**
  (503) when no key is configured and rejects (401) a wrong/absent key.
* ``products.common.findings`` — the normalized ``Finding`` schema, its
  deterministic fingerprint, the confidence->severity mapping, the bounded
  ``ScanRequest``, and the ``findings_from_attack_analysis`` converter.
* Each ``products/<name>/server.py`` FastAPI app — ``/health`` is open and
  ``/scan`` is guarded by the shared auth dependency.

They are intentionally behavior-focused (auth boundaries, serialization,
malformed/oversized input) rather than line-chasing.
"""

from __future__ import annotations

import importlib
import os

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

# A valid (>=32 char) key must exist before any product ``app`` is imported,
# because the health-check modules read it at import time.
API_KEY = "unit-test-key-abcdefghijklmnop-0123456789"
os.environ["MLSEC_API_KEY"] = API_KEY

from products.common import auth  # noqa: E402
from products.common.findings import (  # noqa: E402
    Finding,
    ScanRequest,
    ScanResponse,
    _confidence_to_severity,
    findings_from_attack_analysis,
)

PRODUCTS = [
    "mcp_gateway",
    "hf_scanner",
    "llm_redteam",
    "model_privacy",
    "adv_ml",
    "dataset_poison",
]

# Services that implement an authenticated /scan endpoint. hf_scanner and
# adv_ml are currently health-only stubs (no /scan), so POST /scan is a 404
# there rather than a 401 — the tests assert that reality rather than forcing
# an endpoint that does not exist.
SCAN_PRODUCTS = ["mcp_gateway", "llm_redteam", "model_privacy", "dataset_poison"]
HEALTH_ONLY_PRODUCTS = ["hf_scanner", "adv_ml"]


# --------------------------------------------------------------------------- #
# Shared auth
# --------------------------------------------------------------------------- #
def test_configured_api_key_returns_configured_value():
    assert auth.configured_api_key() == API_KEY


def test_configured_api_key_fails_closed_when_missing(monkeypatch):
    monkeypatch.setenv("MLSEC_API_KEY", "")
    with pytest.raises(HTTPException) as exc:
        auth.configured_api_key()
    assert exc.value.status_code == 503


def test_configured_api_key_fails_closed_when_too_short(monkeypatch):
    monkeypatch.setenv("MLSEC_API_KEY", "short")
    with pytest.raises(HTTPException) as exc:
        auth.configured_api_key()
    assert exc.value.status_code == 503


def test_require_api_key_accepts_correct_key():
    # Correct key: dependency returns None (no exception).
    assert auth.require_api_key(API_KEY) is None


def test_require_api_key_rejects_wrong_key():
    with pytest.raises(HTTPException) as exc:
        auth.require_api_key("wrong-key-wrong-key-wrong-key-xx")
    assert exc.value.status_code == 401


def test_require_api_key_rejects_empty_key():
    with pytest.raises(HTTPException) as exc:
        auth.require_api_key("")
    assert exc.value.status_code == 401


# --------------------------------------------------------------------------- #
# Findings schema
# --------------------------------------------------------------------------- #
def test_confidence_to_severity_mapping():
    assert _confidence_to_severity("High") == "high"
    assert _confidence_to_severity("Medium") == "medium"
    assert _confidence_to_severity("Low") == "low"
    assert _confidence_to_severity("nonsense") == "info"


def test_finding_fingerprint_is_deterministic_and_scoped():
    f1 = Finding(source="s", rule_id="R1", severity="high", title="t", technique="T1059")
    f2 = Finding(source="s", rule_id="R1", severity="low", title="t", technique="T1059")
    f3 = Finding(source="s", rule_id="R2", severity="high", title="t", technique="T1059")
    # fingerprint ignores severity but depends on rule_id/technique/title/source
    assert f1.fingerprint == f2.fingerprint
    assert f1.fingerprint != f3.fingerprint
    assert len(f1.fingerprint) == 16


def test_scan_request_rejects_empty_and_oversized():
    with pytest.raises(Exception):
        ScanRequest(content="")
    with pytest.raises(Exception):
        ScanRequest(content="x" * 200_001)
    # A valid bounded request is accepted.
    assert ScanRequest(content="hello").content == "hello"


def test_findings_from_attack_analysis_converts_detections():
    analysis = {
        "detections": [
            {
                "technique": "T1059 Command and Scripting Interpreter",
                "sub_technique": "T1059.001 PowerShell",
                "confidence": "High",
                "tactic": "execution",
                "matrix": "enterprise",
                "evidence": ["powershell -enc"],
                "recommended_action": "block",
            }
        ]
    }
    findings = findings_from_attack_analysis("mcp_gateway", analysis)
    assert len(findings) == 1
    f = findings[0]
    assert f.source == "mcp_gateway"
    assert f.severity == "high"
    assert f.rule_id == "PowerShell"  # last token of sub_technique
    assert f.evidence == ["powershell -enc"]


def test_findings_from_attack_analysis_empty_is_empty():
    assert findings_from_attack_analysis("x", {}) == []


def test_scan_response_roundtrips():
    f = Finding(source="s", rule_id="R1", severity="high", title="t")
    resp = ScanResponse(source="s", finding_count=1, findings=[f])
    assert resp.finding_count == 1
    assert resp.findings[0].rule_id == "R1"


# --------------------------------------------------------------------------- #
# Every product server: /health open, /scan guarded
# --------------------------------------------------------------------------- #
@pytest.fixture(params=PRODUCTS)
def product_client(request):
    mod = importlib.import_module(f"products.{request.param}.server")
    return request.param, TestClient(mod.app)


def test_product_health_is_open(product_client):
    name, client = product_client
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
    assert resp.json()["product"] == name


@pytest.fixture(params=SCAN_PRODUCTS)
def scan_client(request):
    mod = importlib.import_module(f"products.{request.param}.server")
    return request.param, TestClient(mod.app)


def test_scan_service_requires_auth(scan_client):
    _name, client = scan_client
    # Missing key -> 401 (auth configured because MLSEC_API_KEY is set).
    resp = client.post("/scan", json={"content": "some content"})
    assert resp.status_code == 401


def test_scan_service_accepts_valid_key(scan_client):
    _name, client = scan_client
    resp = client.post(
        "/scan",
        json={"content": "benign content"},
        headers={"x-api-key": API_KEY},
    )
    # Authorized: either a 200 scan response or a validation error, never 401.
    assert resp.status_code != 401


@pytest.fixture(params=HEALTH_ONLY_PRODUCTS)
def health_only_client(request):
    mod = importlib.import_module(f"products.{request.param}.server")
    return request.param, TestClient(mod.app)


def test_health_only_service_has_no_scan_endpoint(health_only_client):
    _name, client = health_only_client
    # These stubs expose only /health; /scan is not implemented (404).
    resp = client.post("/scan", json={"content": "x"})
    assert resp.status_code == 404
