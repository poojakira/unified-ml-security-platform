# RUNBOOK — unified-ml-security-platform

## Prerequisites

- Docker 20.10+ and Docker Compose v2
- Python 3.11+ (for local development)
- 8 GB RAM minimum (16 GB recommended for all 8 services)
- Ports 8000 and 8443 available (only the gateway binds to the host)

## Environment Variables (Required)

```bash
export API_KEY="your-api-key-minimum-32-characters-long"
export PULSENET_JWT_SECRET="your-pulsenet-jwt-secret-min-32-chars"
```

The compose file uses `${API_KEY:?}` syntax — services will refuse to start if these are unset.

## Local Development

```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

## Services

| Service | Internal Port | Docker Service Name | Description |
|---------|---------------|---------------------|-------------|
| Gateway | 8000 (HTTP), 8443 (HTTPS) | `gateway` | FastAPI reverse proxy, API key auth |
| HF Scanner | 8001 | `hf-scanner` | Model supply chain scanning |
| MCP Gateway | 8002 | `mcp-gateway` | MCP agent security monitoring |
| Adversarial ML | 8003 | `adv-ml` | Adversarial robustness evaluation |
| LLM Red-team | 8004 | `llm-redteam` | LLM prompt injection testing |
| Dataset Poison | 8005 | `dataset-poison` | Dataset poisoning detection |
| Model Privacy | 8006 | `model-privacy` | Privacy attack evaluation |
| PulseNet | 8007 | `pulsenet` | RUL forecasting with FDIA detection (archived) |

All product services run `spec_service.py` (a stdlib HTTP stub that responds to `/health` with 200 and all other routes with 501). They do NOT run the `products/*/server.py` FastAPI wrappers — those are dead code.

## Network Architecture

- All services are on the `mlsec-internal` bridge network with `internal: true` (no outbound internet).
- Only the gateway binds to host ports 8000 and 8443.
- Product services are only reachable from within the Docker network via their service names (e.g., `http://hf-scanner:8001`).

## Bring Up Services (Production)

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

## Health Checks

```bash
# Gateway health (unauthenticated, for load balancer probes):
curl http://localhost:8000/health
# {"status":"healthy","version":"1.0.0"}

# Authenticated service inventory:
curl -H "X-API-Key: $API_KEY" http://localhost:8000/status
# {"status":"operational","services":["adv_ml","dataset_poison","hf_scanner","llm_redteam","mcp_gateway","model_privacy"],"total":6}

# Docker-level health status:
docker compose -f docker-compose.prod.yml ps
# All containers should show "Up (healthy)"
```

## Routing Requests Through the Gateway

All requests go through the gateway on port 8000 with the `X-API-Key` header:

```bash
# Example: route to HF scanner
curl -X POST http://localhost:8000/hf_scanner/scan \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model_id": "suspicious-org/model-name"}'

# Example: route to adversarial ML lab
curl -X POST http://localhost:8000/adv_ml/eval/attack \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"attack": "pgd", "eps": 0.031, "steps": 20}'
```

The gateway extracts the first path segment as the service name and proxies to the corresponding internal service. Unknown services return 404. Timeouts return 504. Upstream errors return 502 with an opaque `request_id`.

## Logs

```bash
# All services:
docker compose -f docker-compose.prod.yml logs -f

# Single service:
docker compose -f docker-compose.prod.yml logs -f gateway
docker compose -f docker-compose.prod.yml logs -f hf-scanner

# Last 100 lines:
docker compose -f docker-compose.prod.yml logs --tail=100 adv-ml
```

## Restart a Service

```bash
docker compose -f docker-compose.prod.yml restart hf-scanner
```

## Teardown

```bash
# Stop and remove containers, networks:
docker compose -f docker-compose.prod.yml down

# Also remove images built by compose:
docker compose -f docker-compose.prod.yml down --rmi local
```

## Resource Limits (Production)

| Service | CPU Limit | Memory Limit |
|---------|-----------|--------------|
| gateway | 2 cores | 2 GB |
| hf-scanner | 1 core | 1 GB |
| mcp-gateway | 1 core | 1 GB |
| adv-ml | 2 cores | 4 GB |
| llm-redteam | 1 core | 2 GB |
| dataset-poison | 1 core | 1 GB |
| model-privacy | 1 core | 1 GB |
| pulsenet | 1 core | 1 GB |

Total: 10 CPU cores, 13 GB memory.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Gateway returns 401 | Verify `X-API-Key` header matches `$API_KEY` (min 32 chars) |
| Gateway returns 404 for a service | Check service name matches one of: `hf_scanner`, `mcp_gateway`, `adv_ml`, `llm_redteam`, `dataset_poison`, `model_privacy` |
| Gateway returns 504 | Target service is down or taking >30s. Check `docker compose ps` and service logs |
| Gateway returns 502 | Upstream service error. Check logs with the `request_id` from the error response |
| Product service returns 501 | Expected — stub services only implement `/health`. Deploy from product source repos for full functionality |
| Container restart loop | Check `docker compose logs <svc>` for startup errors. Ensure `API_KEY` and `PULSENET_JWT_SECRET` are set |
| Port 8000 conflict | Stop conflicting process or change gateway port mapping in compose file |
| OOM kills | Increase Docker memory limit in Docker Desktop settings |
| Network unreachable between services | `docker compose down && docker compose up -d` to reset the `mlsec-internal` network |
| Stale images after code change | `docker compose -f docker-compose.prod.yml up -d --build --force-recreate` |
