#!/usr/bin/env python3
"""
Unified Gateway Server - Entry Point
Requires distinct gateway and per-service credentials. Fails fast if missing.
"""

import hmac
import logging
import os
import sys
import uuid
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import Body, Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

# External caller authentication is intentionally separate from service-to-service
# credentials. Reusing one universal key across every backend turns compromise of
# any single service into compromise of the whole platform.
GATEWAY_API_KEY = os.environ.get("GATEWAY_API_KEY")
if not GATEWAY_API_KEY:
    print("FATAL: GATEWAY_API_KEY environment variable is required", file=sys.stderr)
    sys.exit(1)

if len(GATEWAY_API_KEY) < 32:
    print("FATAL: GATEWAY_API_KEY must be at least 32 characters", file=sys.stderr)
    sys.exit(1)

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

GATEWAY_VERSION = "1.0.0"
MAX_PROXY_BODY_BYTES = int(os.environ.get("GATEWAY_MAX_BODY_BYTES", str(2 * 1024 * 1024)))

# Product service URLs (internal Docker network).
# Only route repositories that expose a real long-running HTTP contract.
# Batch evaluators without an HTTP contract (HF scanner CLI and adversarial ML)
# remain outside the synchronous proxy. Model privacy is routed because it now
# exposes an authenticated, bounded assessment service.
SERVICE_URLS = {
    "mcp_gateway": "http://mcp-gateway:8080",
    "llm_redteam": "http://llm-redteam:8000",
    "dataset_poison": "http://dataset-poison:8000",
    "model_privacy": "http://model-privacy:8006",
}

SERVICE_KEY_ENV = {
    "mcp_gateway": "MCP_GATEWAY_API_KEY",
    "llm_redteam": "LLM_REDTEAM_API_KEY",
    "dataset_poison": "DATASET_POISON_API_KEY",
    "model_privacy": "MODEL_PRIVACY_API_KEY",
}

def _service_key(service: str) -> str:
    env_name = SERVICE_KEY_ENV[service]
    value = os.environ.get(env_name, "")
    if not value or len(value) < 32:
        raise RuntimeError(f"{env_name} must be configured with at least 32 characters")
    return value

# Validate service credentials at startup so the gateway can never come up in a
# partially authenticated state.
for _service_name in SERVICE_URLS:
    _service_key(_service_name)

SERVICES = SERVICE_URLS


async def _read_bounded_body(request: Request) -> bytes:
    """Read a request body without allowing unbounded proxy buffering."""
    declared = request.headers.get("content-length")
    if declared:
        try:
            if int(declared) > MAX_PROXY_BODY_BYTES:
                raise HTTPException(status_code=413, detail="Request body too large")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid Content-Length header") from exc

    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_PROXY_BODY_BYTES:
            raise HTTPException(status_code=413, detail="Request body too large")
        chunks.append(chunk)
    return b"".join(chunks)


# Only explicitly approved request headers cross the trust boundary. The
# gateway's own API key is never forwarded from the external caller.
FORWARDED_REQUEST_HEADERS = frozenset(
    {
        "accept",
        "accept-encoding",
        "content-type",
        "user-agent",
        "x-request-id",
        "traceparent",
        "tracestate",
    }
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage a shared httpx.AsyncClient across the application lifetime."""
    app.state.http_client = httpx.AsyncClient(timeout=30.0)
    yield
    await app.state.http_client.aclose()


app = FastAPI(title="MLSec Platform Gateway", version=GATEWAY_VERSION, lifespan=lifespan)


async def verify_api_key(api_key: str = Depends(api_key_header)):
    """Authenticate the external caller without exposing key-comparison timing."""
    if not api_key or not hmac.compare_digest(api_key, GATEWAY_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


@app.get("/health")
async def health():
    """Health check — no auth required for load balancer."""
    return {"status": "healthy", "version": GATEWAY_VERSION}


@app.get("/status")
async def status(api_key: str = Depends(verify_api_key)):
    """Authenticated service inventory for operators."""
    return {
        "status": "operational",
        "services": sorted(SERVICE_URLS),
        "total": len(SERVICE_URLS),
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
    if service not in SERVICE_URLS:
        raise HTTPException(status_code=404, detail=f"Unknown service: {service}")

    target_url = f"{SERVICE_URLS[service]}/{path}"
    client: httpx.AsyncClient = request.app.state.http_client

    try:
        body = await _read_bounded_body(request)
        headers = {
            key: value
            for key, value in request.headers.items()
            if key.lower() in FORWARDED_REQUEST_HEADERS
        }

        # Propagate the authenticated gateway identity explicitly. This keeps
        # service authentication separate from caller-supplied Authorization or
        # Cookie headers, neither of which crosses this boundary implicitly.
        headers[API_KEY_NAME] = _service_key(service)

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
            headers={
                key: value
                for key, value in resp.headers.items()
                if key.lower() not in {"content-length", "transfer-encoding", "connection"}
            },
        )
    except HTTPException:
        # Preserve local validation/authentication decisions such as 413 rather
        # than translating them into an upstream 502.
        raise
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Service timeout")
    except Exception as e:
        req_id = str(uuid.uuid4())[:8]
        logging.getLogger("gateway").error(
            "Service error [req=%s service=%s]: %s", req_id, service, str(e)
        )
        raise HTTPException(
            status_code=502,
            detail={"error": "upstream_service_error", "request_id": req_id},
        ) from e


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)  # nosec B104