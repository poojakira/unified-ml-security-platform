"""
HuggingFace Model Provenance Scanner — Production Server

Real integration with hf-model-provenance-scanner package.
Replaces stub that returned {error: "implementation_not_bundled"}.
"""

import logging
import time
import traceback
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Real integration imports
from scanner import __version__ as SCANNER_VERSION
from scanner.cli import build_scan_config, run_scan
from scanner.core.provenance import ProvenanceChecker
from scanner.core.signatures import SignatureVerifier
from scanner.core.supply_chain import SupplyChainAnalyzer
from scanner.models import ScanResult, Finding, Severity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="HF Model Provenance Scanner Service",
    version=SCANNER_VERSION,
    description="Scans HuggingFace models for provenance, signature, and supply chain issues.",
)

# --- Request / Response Models ---


class ModelConfig(BaseModel):
    """Configuration for a model scan request."""

    model_id: str = Field(..., description="HuggingFace model identifier (e.g., 'org/model-name')")
    revision: Optional[str] = Field(default="main", description="Model revision/branch to scan")
    scan_depth: Optional[str] = Field(default="standard", description="Scan depth: quick, standard, deep")
    check_signatures: bool = Field(default=True, description="Verify cryptographic signatures")
    check_provenance: bool = Field(default=True, description="Check model provenance chain")
    check_supply_chain: bool = Field(default=True, description="Analyze supply chain risks")
    hf_token: Optional[str] = Field(default=None, description="HuggingFace API token for private models")
    additional_checks: Optional[List[str]] = Field(default=None, description="Additional check IDs to run")


class ScanResponse(BaseModel):
    """Response from a completed scan."""

    scan_id: str
    model_id: str
    revision: str
    status: str
    duration_ms: float
    findings: List[Dict[str, Any]]
    summary: Dict[str, Any]
    metadata: Dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    scanner_version: str
    checks_available: List[str]
    uptime_seconds: float


# --- Service State ---

_start_time = time.time()


# --- Endpoints ---


@app.get("/health", response_model=HealthResponse)
async def health():
    """Return real scanner version and available checks."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        scanner_version=SCANNER_VERSION,
        checks_available=[
            "signature_verification",
            "provenance_chain",
            "supply_chain_analysis",
            "model_card_validation",
            "license_compliance",
            "dependency_audit",
        ],
        uptime_seconds=round(time.time() - _start_time, 2),
    )


@app.post("/scan", response_model=ScanResponse)
async def scan_model(config: ModelConfig, request: Request):
    """
    Run a full provenance scan on a HuggingFace model.

    Integrates with scanner.cli to execute the same logic as the CLI tool,
    but returns structured JSON findings.
    """
    scan_start = time.time()
    scan_id = f"scan-{int(scan_start * 1000)}"

    logger.info(f"[{scan_id}] Starting scan for model: {config.model_id}@{config.revision}")

    try:
        # Build scan configuration matching CLI behavior
        scan_config = build_scan_config(
            model_id=config.model_id,
            revision=config.revision,
            depth=config.scan_depth,
            token=config.hf_token,
        )

        # Initialize checkers based on request
        checkers = []

        if config.check_signatures:
            checkers.append(SignatureVerifier(scan_config))

        if config.check_provenance:
            checkers.append(ProvenanceChecker(scan_config))

        if config.check_supply_chain:
            checkers.append(SupplyChainAnalyzer(scan_config))

        # Execute scan through the scanner's run_scan pipeline
        result: ScanResult = run_scan(
            config=scan_config,
            checkers=checkers,
            additional_checks=config.additional_checks,
        )

        # Convert findings to serializable format
        findings = []
        for finding in result.findings:
            findings.append({
                "id": finding.id,
                "severity": finding.severity.value,
                "category": finding.category,
                "title": finding.title,
                "description": finding.description,
                "location": finding.location,
                "remediation": finding.remediation,
                "confidence": finding.confidence,
                "references": finding.references or [],
            })

        duration_ms = round((time.time() - scan_start) * 1000, 2)

        # Build summary
        severity_counts = {}
        for f in findings:
            sev = f["severity"]
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        summary = {
            "total_findings": len(findings),
            "by_severity": severity_counts,
            "risk_score": result.risk_score,
            "pass": result.risk_score < 7.0,
            "checks_executed": len(checkers) + len(config.additional_checks or []),
        }

        logger.info(
            f"[{scan_id}] Scan complete: {len(findings)} findings, "
            f"risk_score={result.risk_score}, duration={duration_ms}ms"
        )

        return ScanResponse(
            scan_id=scan_id,
            model_id=config.model_id,
            revision=config.revision,
            status="completed",
            duration_ms=duration_ms,
            findings=findings,
            summary=summary,
            metadata={
                "scanner_version": SCANNER_VERSION,
                "scan_depth": config.scan_depth,
                "checks_enabled": {
                    "signatures": config.check_signatures,
                    "provenance": config.check_provenance,
                    "supply_chain": config.check_supply_chain,
                },
            },
        )

    except FileNotFoundError as e:
        logger.error(f"[{scan_id}] Model not found: {e}")
        raise HTTPException(status_code=404, detail=f"Model not found: {config.model_id}")

    except PermissionError as e:
        logger.error(f"[{scan_id}] Access denied: {e}")
        raise HTTPException(
            status_code=403,
            detail="Access denied. Provide a valid hf_token for private models.",
        )

    except Exception as e:
        logger.error(f"[{scan_id}] Scan failed: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Scan failed: {str(e)}",
        )


@app.post("/scan/batch")
async def scan_batch(configs: List[ModelConfig]):
    """Scan multiple models in sequence, returning aggregated results."""
    results = []
    for config in configs:
        try:
            from starlette.testclient import TestClient

            # Re-use the scan endpoint logic
            scan_config = build_scan_config(
                model_id=config.model_id,
                revision=config.revision,
                depth=config.scan_depth,
                token=config.hf_token,
            )
            result: ScanResult = run_scan(config=scan_config)
            results.append({
                "model_id": config.model_id,
                "status": "completed",
                "risk_score": result.risk_score,
                "finding_count": len(result.findings),
            })
        except Exception as e:
            results.append({
                "model_id": config.model_id,
                "status": "failed",
                "error": str(e),
            })

    return {"batch_size": len(configs), "results": results}


@app.get("/scan/{scan_id}/status")
async def scan_status(scan_id: str):
    """Check status of a previously submitted scan (for async mode)."""
    # In synchronous mode, scans complete immediately
    return {"scan_id": scan_id, "status": "completed_or_not_found"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
