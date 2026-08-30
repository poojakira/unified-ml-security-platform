"""Minimal health-check server for pulsenet product."""
from __future__ import annotations

import os

from fastapi import FastAPI

MLSEC_API_KEY = os.environ.get("MLSEC_API_KEY", "")

app = FastAPI(title="pulsenet", docs_url=None, redoc_url=None)


@app.get("/health")
async def health():
    return {"status": "healthy", "product": "pulsenet"}
