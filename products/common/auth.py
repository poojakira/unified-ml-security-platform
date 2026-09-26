"""Shared service authentication for product services.

Every product service authenticates callers with a constant-time comparison
against MLSEC_API_KEY and fails closed (503) when no key is configured, so a
misconfigured service cannot silently serve unauthenticated scans.
"""

from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException

MIN_KEY_LENGTH = 32


def configured_api_key() -> str:
    key = os.environ.get("MLSEC_API_KEY", "")
    if len(key) < MIN_KEY_LENGTH:
        raise HTTPException(status_code=503, detail="Service auth is not configured")
    return key


def require_api_key(x_api_key: str = Header(default="")) -> None:
    """FastAPI dependency: constant-time API-key check, fails closed."""
    expected = configured_api_key()
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")
