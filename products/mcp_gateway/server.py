"""mcp_gateway product service: authenticated scan endpoint returning
normalized ATT&CK findings over submitted MCP tool-call / server content."""

from __future__ import annotations

from fastapi import Depends, FastAPI

from attacks.attack_v19_detector import analyze_attack_v19
from products.common.auth import require_api_key
from products.common.findings import (
    ScanRequest,
    ScanResponse,
    findings_from_attack_analysis,
)

SOURCE = "mcp_gateway"
app = FastAPI(title=SOURCE, docs_url=None, redoc_url=None)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "product": SOURCE}


@app.post("/scan", response_model=ScanResponse, dependencies=[Depends(require_api_key)])
async def scan(request: ScanRequest) -> ScanResponse:
    analysis = analyze_attack_v19(request.content)
    findings = findings_from_attack_analysis(SOURCE, analysis)
    return ScanResponse(source=SOURCE, finding_count=len(findings), findings=findings)
