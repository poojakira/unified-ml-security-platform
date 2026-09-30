"""Common bounds for directly accessed product services."""
import hashlib
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from products.common.body_limit import RequestBodyLimit


def configure_security(app: FastAPI) -> None:
    windows: dict[str, list[float]] = {}
    app.add_middleware(RequestBodyLimit, max_bytes=1024 * 1024)

    @app.middleware('http')
    async def boundary(request: Request, call_next):
        if request.url.path != '/health':
            now = time.monotonic()
            cutoff = now - 60
            for key in list(windows):
                if not windows[key] or windows[key][-1] <= cutoff:
                    del windows[key]
            peer = request.client.host if request.client else 'unknown'
            identity = hashlib.sha256(peer.encode()).hexdigest()
            if identity not in windows and len(windows) >= 4096:
                return JSONResponse({'detail': 'Rate limit exceeded'}, status_code=429)
            hits = windows.setdefault(identity, [])
            hits[:] = [stamp for stamp in hits if stamp > cutoff]
            if len(hits) >= 60:
                return JSONResponse({'detail': 'Rate limit exceeded'}, status_code=429)
            hits.append(now)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Cache-Control'] = 'no-store'
        return response
