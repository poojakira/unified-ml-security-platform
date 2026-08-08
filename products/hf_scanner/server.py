"""FastAPI wrapper around hf-model-provenance-scanner.

Exposes the local-scan functionality as a REST endpoint.
Requires the scanner package installed: pip install hf-model-provenance-scanner
"""
from __future__ import annotations

import os
import traceback

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

_API_KEY = os.environ.get("MLSEC_API_KEY", "")
if not _API_KEY:
    raise RuntimeError("MLSEC_API_KEY env var not set")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Depends(api_key_header)):
    if not api_key or api_key != _API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


app = FastAPI(title="hf_scanner", version="1.0.0")

# Attempt import of scanner package
_scanner_available = False
try:
    from scanner.cli import scan_local
    from scanner.models import ScanResult, Severity
    from scanner.config import load_config
    from scanner.risk import compute_risk
    _scanner_available = True
except ImportError:
    pass


class ScanRequest(BaseModel):
    """Request body for local model scan."""
    path: str


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "product": "hf_scanner",
        "port": 8001,
        "scanner_available": _scanner_available,
    }


@app.post("/scan", dependencies=[Depends(verify_api_key)])
async def scan(request: ScanRequest) -> dict:
    """Scan a local model path for supply-chain risks."""
    if not _scanner_available:
        raise HTTPException(
            status_code=503,
            detail="scanner package not installed. Install hf-model-provenance-scanner.",
        )

    if not os.path.exists(request.path):
        raise HTTPException(status_code=400, detail=f"Path not found: {request.path}")

    try:
        config = load_config(None)
        result = ScanResult(target=request.path, findings=[])
        scan_local(result, request.path, config)
        risk_score = compute_risk(result.findings)

        findings_out = []
        for f in result.findings:
            findings_out.append({
                "rule_id": f.rule_id,
                "severity": f.severity.value if isinstance(f.severity, Severity) else str(f.severity),
                "message": f.message,
                "file": f.file_path,
            })

        return {
            "target": request.path,
            "findings": findings_out,
            "total_findings": len(findings_out),
            "risk_score": risk_score,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Scan failed: {str(e)}\n{traceback.format_exc()}"
        )
