from __future__ import annotations

import pytest

from product_registry import PRODUCT_RELEASE_ENV, release_inventory, valid_release_id


def test_release_ids_accept_only_immutable_git_or_oci_identifiers():
    assert valid_release_id("a" * 40)
    assert valid_release_id("sha256:" + "b" * 64)
    assert not valid_release_id("main")
    assert not valid_release_id("latest")
    assert not valid_release_id("v1.2.3")
    assert not valid_release_id("sha256:short")


def test_production_inventory_fails_closed_without_pinned_releases(monkeypatch):
    for env_name in PRODUCT_RELEASE_ENV.values():
        monkeypatch.delenv(env_name, raising=False)
    with pytest.raises(RuntimeError, match="must contain"):
        release_inventory(require_pinned=True)


def test_production_inventory_records_exact_child_releases(monkeypatch):
    values = {
        "MCP_GATEWAY_RELEASE": "1" * 40,
        "LLM_REDTEAM_RELEASE": "2" * 40,
        "DATASET_POISON_RELEASE": "sha256:" + "3" * 64,
        "MODEL_PRIVACY_RELEASE": "4" * 40,
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)

    inventory = release_inventory(require_pinned=True)
    assert inventory["mcp_gateway"]["release_id"] == values["MCP_GATEWAY_RELEASE"]
    assert all(item["pinned"] is True for item in inventory.values())
