"""FastAPI wrapper around adversarial-ml-lab benchmark harness.

Exposes the robustness benchmark runner as a REST endpoint.
Requires: pip install adversarial-ml-lab (with torch dependencies)
"""
from __future__ import annotations

import os
import traceback
from typing import Any

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

_API_KEY = os.environ.get("MLSEC_API_KEY", "")
if not _API_KEY:
    raise RuntimeError("MLSEC_API_KEY env var not set")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Depends(api_key_header)):
    if not api_key or api_key != _API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


app = FastAPI(title="adv_ml", version="1.0.0")

# Attempt import of adversarial-ml-lab
_adv_lab_available = False
try:
    from adv_lab.eval.harness import run_benchmark, BenchmarkResult
    _adv_lab_available = True
except ImportError:
    pass


class BenchmarkRequest(BaseModel):
    """Request body for robustness benchmark.

    model_path: path to a saved torch model (.pt file)
    epsilon: L-inf perturbation budget (default 0.03)
    n_samples: number of samples to evaluate (default 500)
    """
    model_config = {"protected_namespaces": ()}

    model_path: str
    epsilon: float = 0.03
    n_samples: int = 500


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "product": "adv_ml",
        "port": 8003,
        "adv_lab_available": _adv_lab_available,
    }


@app.post("/benchmark", dependencies=[Depends(verify_api_key)])
async def benchmark(request: BenchmarkRequest) -> dict[str, Any]:
    """Run FGSM/PGD/C&W robustness benchmark on a saved model.

    NOTE: Requires a PyTorch model and corresponding dataloader.
    This endpoint loads the model from disk and runs the attack ladder.
    """
    if not _adv_lab_available:
        raise HTTPException(
            status_code=503,
            detail="adv_lab package not installed. Install adversarial-ml-lab.",
        )

    if not os.path.exists(request.model_path):
        raise HTTPException(
            status_code=400, detail=f"Model path not found: {request.model_path}"
        )

    try:
        import torch

        model = torch.load(request.model_path, map_location="cpu", weights_only=False)
        model.eval()

        # For a real deployment, the dataloader would be configured per-model.
        # This endpoint requires a bundled test dataset or a follow-up config.
        raise HTTPException(
            status_code=501,
            detail="Benchmark requires a paired dataloader. "
            "Use the CLI directly: python -m adv_lab.eval.cli --model <path>",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Benchmark failed: {str(e)}\n{traceback.format_exc()}",
        )
