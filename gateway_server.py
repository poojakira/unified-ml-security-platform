#!/usr/bin/env python3
"""
Unified Gateway Server - Entry Point
Requires distinct gateway and per-service credentials. Fails fast if missing.
"""

import asyncio
import hashlib
import hmac
import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import Body, Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

from products.common.body_limit import RequestBodyLimit
from product_registry import release_inventory

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
GATEWAY_RATE_LIMIT_RPM = int(os.environ.get("GATEWAY_RATE_LIMIT_RPM", "300"))
GATEWAY_MAX_CONCURRENT_CORRELATIONS = int(
    os.environ.get("GATEWAY_MAX_CONCURRENT_CORRELATIONS", "8")
)
_CORRELATION_MODE = os.environ.get("GATEWAY_CORRELATION_MODE", "fail_closed").strip().lower()
_rate_windows: dict[str, list[float]] = {}
if MAX_PROXY_BODY_BYTES < 1024 or MAX_PROXY_BODY_BYTES > 16 * 1024 * 1024:
    raise RuntimeError("GATEWAY_MAX_BODY_BYTES must be between 1 KiB and 16 MiB")
if GATEWAY_RATE_LIMIT_RPM < 1 or GATEWAY_RATE_LIMIT_RPM > 10000:
    raise RuntimeError("GATEWAY_RATE_LIMIT_RPM must be between 1 and 10000")
if GATEWAY_MAX_CONCURRENT_CORRELATIONS < 1 or GATEWAY_MAX_CONCURRENT_CORRELATIONS > 128:
    raise RuntimeError("GATEWAY_MAX_CONCURRENT_CORRELATIONS must be between 1 and 128")
if _CORRELATION_MODE not in {"fail_closed", "best_effort"}:
    raise RuntimeError("GATEWAY_CORRELATION_MODE must be 'fail_closed' or 'best_effort'")

_correlate_slots = asyncio.Semaphore(GATEWAY_MAX_CONCURRENT_CORRELATIONS)

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
_PRODUCT_RELEASES = release_inventory(
    require_pinned=os.environ.get("PLATFORM_ENV", "").lower() == "production"
)


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


def _consume_rate_limit(identity: str) -> bool:
    now = time.time()
    cutoff = now - 60.0
    for key in list(_rate_windows):
        if not _rate_windows[key] or _rate_windows[key][-1] <= cutoff:
            del _rate_windows[key]
    if identity not in _rate_windows and len(_rate_windows) >= 4096:
        return False
    bucket = _rate_windows.setdefault(identity, [])
    bucket[:] = [ts for ts in bucket if ts > cutoff]
    if len(bucket) >= GATEWAY_RATE_LIMIT_RPM:
        return False
    bucket.append(now)
    if len(_rate_windows) > 4096:
        stale = [key for key, values in _rate_windows.items() if not values or values[-1] <= cutoff]
        for key in stale[:1024]:
            _rate_windows.pop(key, None)
    return True


@app.middleware("http")
async def security_boundary(request: Request, call_next):
    if request.url.path != "/health":
        # Consume the peer budget before credential validation so rotating
        # invalid API keys cannot evade the outer abuse-control boundary.
        peer = request.client.host if request.client else "unknown"
        identity = hashlib.sha256(peer.encode("utf-8")).hexdigest()[:32]
        if not _consume_rate_limit(identity):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": "60"},
            )

        # Authenticate after the peer abuse budget is consumed. Route
        # dependencies retain the same key check as defense in depth.
        supplied_key = request.headers.get(API_KEY_NAME, "")
        if not supplied_key or not hmac.compare_digest(
            supplied_key.encode("utf-8"), GATEWAY_API_KEY.encode("utf-8")
        ):
            return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


# Added after the HTTP security middleware so Starlette places the byte-limit
# middleware outermost. Oversized bodies are rejected before authentication,
# JSON parsing, rate-window mutation, or downstream proxy buffering.
app.add_middleware(RequestBodyLimit, max_bytes=MAX_PROXY_BODY_BYTES)


async def verify_api_key(api_key: str = Depends(api_key_header)):
    """Authenticate the external caller without exposing key-comparison timing."""
    if not api_key or not hmac.compare_digest(
        api_key.encode("utf-8"), GATEWAY_API_KEY.encode("utf-8")
    ):
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
        "product_releases": _PRODUCT_RELEASES,
    }


# Severity ordering for correlated aggregation (highest first).
_SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


@app.post("/correlate")
async def correlate(
    request: Request,
    payload: dict = Body(default_factory=dict),
    api_key: str = Depends(verify_api_key),
):
    """Fan out submitted content to every routed service's /scan, then
    aggregate and de-duplicate the normalized findings into one correlated
    report. This is the cross-service correlation surface: identical findings
    reported by multiple services are merged and annotated with every source
    that observed them.
    """
    content = payload.get("content")
    if not isinstance(content, str) or not content or len(content) > 200_000:
        raise HTTPException(
            status_code=422, detail="content must be a non-empty string <= 200000 chars"
        )

    await _correlate_slots.acquire()
    try:
        client: httpx.AsyncClient = request.app.state.http_client
        merged: dict[str, dict] = {}
        service_status: dict[str, str] = {}

        for service, base_url in SERVICE_URLS.items():
            try:
                resp = await client.post(
                    f"{base_url}/scan",
                    json={"content": content},
                    headers={API_KEY_NAME: _service_key(service)},
                    timeout=15.0,
                )
            except httpx.HTTPError:
                # Preserve partial evidence, but never silently present it as a
                # complete security decision. fail_closed is the default.
                service_status[service] = "unavailable"
                continue

            if resp.status_code != 200:
                service_status[service] = f"error_{resp.status_code}"
                continue
            service_status[service] = "ok"

            for finding in resp.json().get("findings", []):
                # De-duplicate on the identifying fields; merge observing sources.
                key = "|".join(str(finding.get(f)) for f in ("rule_id", "technique", "title"))
                if key in merged:
                    merged[key]["observed_by"].append(finding.get("source"))
                else:
                    entry = dict(finding)
                    entry["observed_by"] = [finding.get("source")]
                    merged[key] = entry

        findings = sorted(
            merged.values(),
            key=lambda f: (
                _SEVERITY_RANK.get(f.get("severity"), 0),
                len(f["observed_by"]),
            ),
            reverse=True,
        )
        complete = len(service_status) == len(SERVICE_URLS) and all(
            value == "ok" for value in service_status.values()
        )
        result = {
            "content_scanned": True,
            "complete": complete,
            "correlation_mode": _CORRELATION_MODE,
            "services_queried": len(SERVICE_URLS),
            "service_status": service_status,
            "correlated_finding_count": len(findings),
            "findings": findings,
        }
        if not complete and _CORRELATION_MODE == "fail_closed":
            return JSONResponse(status_code=503, content=result)
        return result
    finally:
        _correlate_slots.release()


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


@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(service: str, path: str, request: Request, api_key: str = Depends(verify_api_key)):
    if service not in SERVICE_URLS:
        raise HTTPException(status_code=404, detail="Unknown service")
    if ".." in path.split("/") or "://" in path or "\\" in path:
        raise HTTPException(status_code=400, detail="Invalid proxy path")

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
                if key.lower() in {"content-type", "cache-control", "retry-after", "x-request-id"}
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
