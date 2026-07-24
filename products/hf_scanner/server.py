"""Thin FastAPI wrapper around hf_scanner."""
from __future__ import annotations
import os
from fastapi import FastAPI

_API_KEY = os.environ.get("MLSEC_API_KEY")
if not _API_KEY:
    raise RuntimeError("MLSEC_API_KEY env var not set")

app = FastAPI(title="hf_scanner", version="1.0.0")

@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "product": "hf_scanner", "port": 8001}