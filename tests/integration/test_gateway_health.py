import httpx


EXPECTED_SERVICES = {
    "hf_scanner",
    "mcp_gateway",
    "adv_ml",
    "llm_redteam",
    "dataset_poison",
    "model_privacy",
    "pulsenet",
}


def test_gateway_health_endpoint_exposes_expected_services() -> None:
    response = httpx.get("http://localhost:8000/health", timeout=10.0)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert set(payload["services"]) == EXPECTED_SERVICES
