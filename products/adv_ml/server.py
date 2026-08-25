"""Minimal health-check server for adv_ml product."""
from __future__ import annotations

import os

from fastapi import FastAPI

MLSEC_API_KEY = os.environ.get("MLSEC_API_KEY", "")

app = FastAPI(title="adv_ml", docs_url=None, redoc_url=None)


@app.get("/health")
async def health():
    return {"status": "healthy", "product": "adv_ml"}
