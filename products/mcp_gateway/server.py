"""Thin FastAPI wrapper around mcp_gateway."""
from __future__ import annotations
import os
from fastapi import FastAPI

_API_KEY = os.environ.get("MLSEC_API_KEY")
if not _API_KEY:
    raise RuntimeError("MLSEC_API_KEY env var not set")

app = FastAPI(title="mcp_gateway", version="1.0.0")

@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "product": "mcp_gateway", "port": 8002}