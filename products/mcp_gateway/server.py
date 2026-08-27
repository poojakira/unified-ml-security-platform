"""Minimal health-check server for mcp_gateway product."""
from __future__ import annotations

import os

from fastapi import FastAPI

MLSEC_API_KEY = os.environ.get("MLSEC_API_KEY", "")

app = FastAPI(title="mcp_gateway", docs_url=None, redoc_url=None)


@app.get("/health")
async def health():
    return {"status": "healthy", "product": "mcp_gateway"}
