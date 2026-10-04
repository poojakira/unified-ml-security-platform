from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "UPSTREAM_PRODUCTS.json"


def test_upstream_registry_uses_immutable_source_revisions():
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert data["schema_version"] == "upstream-product-registry-v1"
    products = data["products"]
    assert len(products) >= 4

    services = [item["service"] for item in products]
    assert len(services) == len(set(services))

    for item in products:
        assert item["repository"].startswith("poojakira/")
        assert re.fullmatch(r"[0-9a-f]{40}", item["revision"])
        assert item["bundled"] is False
        assert item["contract"]


def test_registry_does_not_claim_deployment_proof():
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    boundary = data["claim_boundary"].lower()
    assert "does not prove" in boundary
    assert "deployed" in boundary
