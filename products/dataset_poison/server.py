"""dataset_poison product service.

Exposes a real, authenticated scan endpoint that runs the in-repo ATT&CK v19
detector over submitted dataset-related content (e.g. suspicious pipeline logs,
dataset descriptors, loader source) and returns normalized findings. This is a
functional service, not a health-only stub: /scan performs real detection.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI

from attacks.attack_v19_detector import analyze_attack_v19
from products.common.auth import require_api_key
from products.common.findings import (
    ScanRequest,
    ScanResponse,
    findings_from_attack_analysis,
)

SOURCE = "dataset_poison"
app = FastAPI(title=SOURCE, docs_url=None, redoc_url=None)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "product": SOURCE}


@app.post("/scan", response_model=ScanResponse, dependencies=[Depends(require_api_key)])
async def scan(request: ScanRequest) -> ScanResponse:
    """Run real detection over submitted content and return normalized findings."""
    analysis = analyze_attack_v19(request.content)
    findings = findings_from_attack_analysis(SOURCE, analysis)
    return ScanResponse(source=SOURCE, finding_count=len(findings), findings=findings)
