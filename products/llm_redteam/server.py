"""Minimal health-check server for llm_redteam product."""
from __future__ import annotations

import os

from fastapi import FastAPI

MLSEC_API_KEY = os.environ.get("MLSEC_API_KEY", "")

app = FastAPI(title="llm_redteam", docs_url=None, redoc_url=None)


@app.get("/health")
async def health():
    return {"status": "healthy", "product": "llm_redteam"}
