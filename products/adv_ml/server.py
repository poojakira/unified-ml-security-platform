"""Thin FastAPI wrapper around adv_ml."""
from __future__ import annotations
import os
from fastapi import FastAPI

_API_KEY = os.environ.get("MLSEC_API_KEY")
if not _API_KEY:
    raise RuntimeError("MLSEC_API_KEY env var not set")

app = FastAPI(title="adv_ml", version="1.0.0")

@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "product": "adv_ml", "port": 8003}