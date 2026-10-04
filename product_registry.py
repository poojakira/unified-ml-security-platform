"""Release provenance for independently released child products.

The control plane owns routing and integration. Product repositories own their
implementations. Production deployments must identify the exact child releases
that were composed so an operator can reproduce the platform state.
"""

from __future__ import annotations

import os
import re

PRODUCT_RELEASE_ENV = {
    "mcp_gateway": "MCP_GATEWAY_RELEASE",
    "llm_redteam": "LLM_REDTEAM_RELEASE",
    "dataset_poison": "DATASET_POISON_RELEASE",
    "model_privacy": "MODEL_PRIVACY_RELEASE",
}

_GIT_SHA = re.compile(r"^[0-9a-f]{40}$", re.I)
_IMAGE_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$", re.I)


def valid_release_id(value: str) -> bool:
    """Accept an immutable Git commit or OCI sha256 digest."""
    value = value.strip()
    return bool(_GIT_SHA.fullmatch(value) or _IMAGE_DIGEST.fullmatch(value))


def release_inventory(*, require_pinned: bool = False) -> dict[str, dict[str, str | bool]]:
    inventory: dict[str, dict[str, str | bool]] = {}
    for product, env_name in PRODUCT_RELEASE_ENV.items():
        raw = os.environ.get(env_name, "").strip()
        pinned = valid_release_id(raw)
        if require_pinned and not pinned:
            raise RuntimeError(
                f"{env_name} must contain a full 40-character Git SHA or sha256 OCI digest"
            )
        inventory[product] = {
            "release_id": raw or "unconfigured",
            "pinned": pinned,
            "source": env_name,
        }
    return inventory
