#!/usr/bin/env python3
"""
Unified ML Security Platform — API Gateway

Aggregates portfolio ML security tools behind a single authenticated endpoint.
Calls scan functions directly from installed packages rather than proxying to
microservices. Missing packages degrade gracefully (reported via /status).
"""

from __future__ import annotations

import os
import sys
import traceback
from typing import Any

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import uvicorn

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    print("FATAL: API_KEY environment variable is required", file=sys.stderr)
    sys.exit(1)

if len(API_KEY) < 32:
    print("FATAL: API_KEY must be at least 32 characters", file=sys.stderr)
    sys.exit(1)

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def verify_api_key(api_key: str = Depends(api_key_header)):
    if not api_key or api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


# ---------------------------------------------------------------------------
# Optional package imports — graceful degradation
# ---------------------------------------------------------------------------

_iam_available = False
_hf_scanner_available = False
_adv_lab_available = False

try:
    from aws_agent_identity_guard import scan_policy_document, Finding as IAMFinding
    _iam_available = True
except ImportError:
    pass

try:
    from scanner.cli import scan_local as _hf_scan_local
    from scanner.models import ScanResult, Finding as HFinding, Severity
    from scanner.config import load_config as _hf_load_config
    from scanner.risk import compute_risk as _hf_compute_risk
    _hf_scanner_available = True
except ImportError:
    pass

try:
    from adv_lab.eval.harness import run_benchmark, BenchmarkResult
    _adv_lab_available = True
except ImportError:
    pass


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Unified ML Security Platform",
    version="1.0.0",
    description="API gateway aggregating ML security tools behind a single endpoint.",
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class IAMScanRequest(BaseModel):
    """IAM policy document to scan."""
    policy_document: dict[str, Any]


class ModelScanRequest(BaseModel):
    """Path to a local model directory or file."""
    path: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    """Health check — no auth required for load balancers."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/status", dependencies=[Depends(verify_api_key)])
async def status():
    """Report which scan services are available (installed vs not)."""
    services = {
        "iam_scanner": {
            "available": _iam_available,
            "package": "aws-agent-identity-guard",
            "endpoint": "POST /scan/iam",
        },
        "hf_scanner": {
            "available": _hf_scanner_available,
            "package": "hf-model-provenance-scanner",
            "endpoint": "POST /scan/model",
        },
        "adv_ml": {
            "available": _adv_lab_available,
            "package": "adversarial-ml-lab",
            "endpoint": "POST /scan/adversarial (requires model + data)",
        },
    }
    installed_count = sum(1 for s in services.values() if s["available"])
    return {
        "status": "operational",
        "services": services,
        "installed": installed_count,
        "total": len(services),
    }


@app.post("/scan/iam", dependencies=[Depends(verify_api_key)])
async def scan_iam(request: IAMScanRequest):
    """Scan an IAM policy document for AI-agent-specific risks.

    Accepts the policy JSON and returns all findings with severity and remediation.
    """
    if not _iam_available:
        raise HTTPException(
            status_code=503,
            detail="aws-agent-identity-guard is not installed. "
            "Install with: pip install aws-agent-identity-guard",
        )

    try:
        findings = scan_policy_document(request.policy_document)
        return {
            "findings": [f.to_dict() for f in findings],
            "total_findings": len(findings),
            "passed": len(findings) == 0,
        }
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Scan error: {str(e)}")


@app.post("/scan/model", dependencies=[Depends(verify_api_key)])
async def scan_model(request: ModelScanRequest):
    """Scan a local model directory or file for supply-chain risks.

    Accepts a filesystem path and runs the HF provenance scanner against it.
    """
    if not _hf_scanner_available:
        raise HTTPException(
            status_code=503,
            detail="hf-model-provenance-scanner is not installed. "
            "Install with: pip install hf-model-provenance-scanner",
        )

    target = request.path
    if not os.path.exists(target):
        raise HTTPException(status_code=400, detail=f"Path does not exist: {target}")

    try:
        config = _hf_load_config(None)
        result = ScanResult(target=target, findings=[])
        _hf_scan_local(result, target, config)
        risk_score = _hf_compute_risk(result.findings)

        findings_out = []
        for f in result.findings:
            findings_out.append({
                "rule_id": f.rule_id,
                "severity": f.severity.value if isinstance(f.severity, Severity) else str(f.severity),
                "message": f.message,
                "file": f.file_path,
            })

        return {
            "target": target,
            "findings": findings_out,
            "total_findings": len(findings_out),
            "risk_score": risk_score,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Scan error: {str(e)}\n{traceback.format_exc()}",
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
