# Incident Runbook — Unified ML Security Platform Gateway

## Overview

This runbook covers operational incidents for the API Gateway that fronts the
product services on the internal Docker network.

The gateway is a **single module** — `gateway_server.py` (FastAPI). There is no
`gateway` package; there are no `gateway.app`, `gateway.auth`, `gateway.proxy`,
`gateway.middleware`, or `gateway.audit` modules.

**Authentication:** `X-API-Key` header only, checked against the `API_KEY`
environment variable. There is no JWT, JWKS, session store, rate limiter, or
metrics endpoint in this gateway.

**Routing:** the gateway proxies `/{service}/{path}` to the matching internal
service URL. Unknown services return 404. Two management endpoints exist:
`/health` (unauthenticated) and `/status` (requires `X-API-Key`).

**Architecture:**
```
Clients → [gateway :8000] → http://hf-scanner:8001
                          → http://mcp-gateway:8002
                          → http://adv-ml:8003
                          → http://llm-redteam:8004
                          → http://dataset-poison:8005
                          → http://model-privacy:8006
```

**On-call contacts:**
- Primary: Platform Engineering (#platform-oncall in Slack)
- Escalation: Security Engineering (#security-oncall in Slack)

---

## Incident Severity Levels

| Level | Description | Response Time | Examples |
|-------|-------------|---------------|----------|
| SEV1 | Complete outage, security bypass | 5 min | Gateway down, auth bypass |
| SEV2 | Partial outage | 15 min | One backend down, high error rate |
| SEV3 | Performance degradation | 1 hour | High latency |
| SEV4 | Minor issue, no user impact | Next business day | Log noise |

---

## INC-001: Gateway Completely Unresponsive

### Symptoms
- `/health` endpoint returns no response or connection refused
- All API calls timeout

### Diagnosis

```bash
# Check gateway container
docker ps | grep gateway
docker logs gateway --tail 100 --since 5m

# Check port binding (gateway listens on 8000)
ss -tlnp | grep 8000

# Check resource usage
docker stats gateway --no-stream
```

### Resolution

1. **Process crashed / container exited:**
   ```bash
   docker restart gateway
   # or via compose
   docker compose up -d gateway
   ```

2. **Missing/invalid API_KEY (fails fast on startup):**
   ```bash
   # The server exits immediately if API_KEY is unset or < 32 chars.
   docker logs gateway --tail 20   # look for "FATAL: API_KEY ..."
   # Set a valid key (>= 32 chars) in the environment / compose and restart.
   docker compose up -d gateway
   ```

3. **Port conflict:**
   ```bash
   lsof -i :8000
   # stop the conflicting process, then restart the gateway
   docker restart gateway
   ```

4. **Configuration sanity check:**
   ```bash
   # The gateway is a single module; import it to validate it loads.
   # (Requires API_KEY to be set, since it is validated at import time.)
   docker exec gateway python -c "import gateway_server; print('Gateway import OK')"
   docker exec gateway env | grep -i API_KEY
   ```

### Post-incident
- Confirm health checks / restart policy are configured
- Verify alerting fired within the expected timeframe

---

## INC-002: Authentication Failures (401)

### Symptoms
- Requests with a valid key receiving 401
- All authenticated requests failing

### Diagnosis

```bash
# Test /status with the configured key (should be 200)
curl -H "X-API-Key: ${API_KEY}" http://localhost:8000/status

# Missing/empty key or wrong key -> 401 "Invalid API key"
curl -i http://localhost:8000/status

# Confirm the key the gateway expects
docker exec gateway env | grep -i API_KEY
```

### Resolution

1. **Key mismatch between client and gateway:**
   ```bash
   # Ensure the client's X-API-Key matches the gateway's API_KEY env var.
   docker exec gateway env | grep API_KEY
   ```

2. **Key rotated in config but process not restarted:**
   ```bash
   # API_KEY is read at process start; restart after changing it.
   docker compose up -d gateway
   ```

### Post-incident
- Audit access during the failure window
- Review key distribution/rotation process (env-var based)

---

## INC-003: Backend Service Unavailable

### Symptoms
- Requests to a specific `/{service}/...` route fail or return 404/502/504
- Gateway `/health` is fine, but a backend is down

### Diagnosis

```bash
# Gateway health (unauthenticated) — should return {"status":"healthy",...}
curl http://localhost:8000/health

# Authenticated service inventory
curl -H "X-API-Key: ${API_KEY}" http://localhost:8000/status

# Check a backend directly
curl http://localhost:8001/health   # hf-scanner
curl http://localhost:8002/health   # mcp-gateway

# From inside the gateway container, over the internal network
docker exec gateway python -c "import httpx; print(httpx.get('http://hf-scanner:8001/health').status_code)"
```

Notes on gateway responses:
- Unknown service name in the path → **404** (`Unknown service: <name>`).
- Upstream timeout → **504** (`Service timeout`).
- Other upstream error → **502** (`upstream_service_error` with a request id).

### Resolution

1. **Backend process crashed:**
   ```bash
   docker restart hf-scanner   # or mcp-gateway, adv-ml, etc.
   sleep 5
   curl http://localhost:8001/health
   ```

2. **Network partition on the internal network:**
   ```bash
   # The internal Docker network is named "mlsec-internal".
   docker network inspect mlsec-internal
   docker network disconnect mlsec-internal hf-scanner
   docker network connect mlsec-internal hf-scanner
   ```

### Post-incident
- Review backend health-check intervals
- Consider a circuit breaker for repeatedly failing upstreams

---

## INC-004: High Latency / Performance Degradation

### Symptoms
- Response times exceed SLA
- Client timeouts increasing

### Diagnosis

```bash
# Time the health/status endpoints and a backend
time curl http://localhost:8000/health
time curl http://localhost:8001/health

# Resource usage
docker stats --no-stream
```

The gateway proxies requests with a shared `httpx.AsyncClient` (30s timeout).
Latency is usually driven by a slow upstream service rather than the gateway.

### Resolution

1. **Slow backend:**
   ```bash
   # Scale the slow backend horizontally
   docker compose up -d --scale hf-scanner=3
   ```

2. **Gateway CPU saturation:**
   ```bash
   # Scale the gateway (stateless — safe to run multiple replicas)
   docker compose up -d --scale gateway=3
   ```

### Post-incident
- Run `pytest tests/test_gateway.py` to validate the gateway after recovery
- Update capacity planning if load has grown

---

## INC-005: Security Incident — Potential Auth Bypass

### Symptoms
- Unexpected 200 responses to requests without a valid `X-API-Key`
- Anomalous traffic to backend services

### Immediate Actions (SEV1)

```bash
# 1. Block suspicious traffic at the host
iptables -A INPUT -s <SUSPICIOUS_IP> -j DROP

# 2. Capture state for forensics
docker logs gateway > /tmp/gateway-forensics-$(date +%s).log

# 3. Verify auth is actually enforced:
#    /status and any /{service}/{path} route require X-API-Key.
curl -i http://localhost:8000/status                      # expect 401 without key
curl -i http://localhost:8000/hf_scanner/health           # expect 401 without key
curl -i -H "X-API-Key: ${API_KEY}" http://localhost:8000/status   # expect 200
```

Note: `/health` is intentionally unauthenticated for load balancers and only
returns `{"status": "healthy", "version": ...}` — no service inventory.

### Resolution

1. **Rotate the API key immediately:**
   ```bash
   # Set a new API_KEY (>= 32 chars) in the environment / compose secret,
   # then restart the gateway so it re-reads the value.
   docker compose up -d gateway
   ```

2. **Roll out a fixed image if a vulnerability is found:**
   ```bash
   docker compose pull gateway
   docker compose up -d gateway
   ```

### Post-incident (MANDATORY)
- Full review of `gateway_server.py` auth path (`verify_api_key`)
- Review all access during the incident window
- Blameless postmortem within 48 hours

---

## INC-006: Disk Space / Log Rotation Issues

### Symptoms
- Container filesystem full
- Logs not rotating

### Diagnosis

```bash
df -h
docker system df
docker inspect gateway --format='{{.LogPath}}'
```

### Resolution

```bash
# Truncate container logs (immediate relief)
truncate -s 0 $(docker inspect gateway --format='{{.LogPath}}')

# Configure log rotation
docker update --log-opt max-size=100m --log-opt max-file=5 gateway

# Clean up unused images/containers
docker system prune -af
```

---

## Runbook Maintenance

| Last reviewed | Reviewer | Changes |
|---------------|----------|---------|
| 2026-08-27 | Platform Engineering | Corrected to match single-module gateway_server.py, X-API-Key auth, /{service}/{path} routing, /health + /status endpoints, and mlsec-internal network |

**Review schedule:** Monthly or after any SEV1/SEV2 incident.
