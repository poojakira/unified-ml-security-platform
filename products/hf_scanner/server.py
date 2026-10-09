"""Minimal health-check server for hf_scanner product."""

from __future__ import annotations

import os

from products.common.security import configure_security
from fastapi import FastAPI

MLSEC_API_KEY = os.environ.get("MLSEC_API_KEY", "")

app = FastAPI(title="hf_scanner", docs_url=None, redoc_url=None)
configure_security(app)


@app.get("/health")
async def health():
    return {"status": "healthy", "product": "hf_scanner"}
