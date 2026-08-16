#!/usr/bin/env python3
"""
Unified Gateway Server - Production Entry Point
Requires API_KEY environment variable. Fails fast if missing.
"""

import os
import sys
from fastapi import FastAPI, Request, HTTPException, Depends, Body
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
import uvicorn
import httpx

# Fail fast if API_KEY not set
API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    print("FATAL: API_KEY environment variable is required", file=sys.stderr)
    sys.exit(1)

if len(API_KEY) < 32:
    print("FATAL: API_KEY must be at least 32 characters", file=sys.stderr)
    sys.exit(1)

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

GATEWAY_VERSION = "1.0.0"

app = FastAPI(title="MLSec Platform Gateway", version=GATEWAY_VERSION)

# Product service URLs (internal Docker network)
SERVICES = {
    "hf_scanner": "http://hf-scanner:8001",
    "mcp_gateway": "http://mcp-gateway:8002",
    "adv_ml": "http://adv-ml:8003",
    "llm_redteam": "http://llm-redteam:8004",
    "dataset_poison": "http://dataset-poison:8005",
    "model_privacy": "http://model-privacy:8006",
    # "pulsenet" removed — archived project; not an active service
}


async def verify_api_key(api_key: str = Depends(api_key_header)):
    if not api_key or api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


@app.get("/health")
async def health():
    """Health check — no auth required for load balancer.

    NOTE: Does not expose service inventory to unauthenticated callers.
    Service list is internal operational information.
    """
    return {"status": "healthy", "version": GATEWAY_VERSION}


@app.get("/status")
async def status(api_key: str = Depends(verify_api_key)):
    """Authenticated service inventory for operators."""
    return {
        "status": "operational",
        "services": sorted(SERVICES),
        "total": len(SERVICES),
    }


@app.post("/scan/iam")
async def scan_iam(
    payload: dict = Body(default_factory=dict),
    api_key: str = Depends(verify_api_key),
):
    """IAM scanner is not bundled in this architecture repository."""
    raise HTTPException(status_code=503, detail="iam_scanner_not_bundled")


@app.post("/scan/model")
async def scan_model(
    payload: dict = Body(default_factory=dict),
    api_key: str = Depends(verify_api_key),
):
    """Model scanner is not bundled in this architecture repository."""
    raise HTTPException(status_code=503, detail="model_scanner_not_bundled")


@app.api_route(
    "/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
)
async def proxy(
    service: str, path: str, request: Request, api_key: str = Depends(verify_api_key)
):
    if service not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Unknown service: {service}")

    target_url = f"{SERVICES[service]}/{path}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            body = await request.body()
            headers = dict(request.headers)
            headers.pop("host", None)
            headers.pop("content-length", None)

            resp = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params,
            )

            return JSONResponse(
                content=resp.json()
                if resp.headers.get("content-type", "").startswith("application/json")
                else resp.text,
                status_code=resp.status_code,
                headers=dict(resp.headers),
            )
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Service timeout")
        except Exception as e:
            # Do not expose internal exception details to clients.
            # Log server-side with request ID for debugging.
            import logging, uuid

            req_id = str(uuid.uuid4())[:8]
            logging.getLogger("gateway").error(
                "Service error [req=%s service=%s]: %s", req_id, service, str(e)
            )
            raise HTTPException(
                status_code=502,
                detail={"error": "upstream_service_error", "request_id": req_id},
            )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)  # nosec B104
