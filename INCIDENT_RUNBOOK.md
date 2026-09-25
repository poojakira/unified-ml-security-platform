# Incident Runbook — Unified ML Security Platform

> **Template for self-hosters, not an operated service.** This is a reference
> incident playbook for someone running the Docker Compose stack themselves.
> There is no operated production deployment, on-call rotation, SLA, or live
> monitoring behind this repository. The topology below describes the Compose
> profile a self-hoster runs, not a service operated by the maintainer.

## Compose topology

```
Clients -> gateway:8000 -> mcp-gateway:8080
                        -> llm-redteam:8000
                        -> dataset-poison:8000
```

The HF provenance scanner, adversarial ML lab, and model-privacy project are
batch/admission tools and are not gateway backends.

The gateway requires `GATEWAY_API_KEY` and three separate backend credentials:
`MCP_GATEWAY_API_KEY`, `LLM_REDTEAM_API_KEY`, and
`DATASET_POISON_API_KEY`.

## First checks

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=200 gateway
curl http://localhost:8000/health
curl -H "X-API-Key: $GATEWAY_API_KEY" http://localhost:8000/status
```

Expected inventory is exactly:
`dataset_poison`, `llm_redteam`, `mcp_gateway`.

## Gateway unavailable

Check startup logs for missing/short credentials. The gateway intentionally
fails startup if any required service identity is absent.

```bash
docker compose -f docker-compose.prod.yml logs --tail=100 gateway
docker compose -f docker-compose.prod.yml config
```

Do not restore service by reusing one universal key. Restore the missing
service-specific credential.

## 401 responses

Confirm the client uses `GATEWAY_API_KEY`, not a backend key:

```bash
curl -i -H "X-API-Key: $GATEWAY_API_KEY" http://localhost:8000/status
```

Rotate only the compromised credential. If an upstream key is rotated, restart
the gateway and that upstream with the same new value.

## 413 responses

The gateway rejected the body before forwarding because it exceeded
`GATEWAY_MAX_BODY_BYTES` (default 2 MiB) or supplied an invalid
`Content-Length`.

Do not increase the limit blindly. Confirm the endpoint genuinely requires a
larger bounded payload and that the upstream has a compatible limit.

## MCP unavailable

```bash
docker compose -f docker-compose.prod.yml logs --tail=200 mcp-gateway
```

The Compose health check uses `/v1/ready`. A process that is live but not
ready must not receive traffic.

## LLM service unavailable or noisy

```bash
docker compose -f docker-compose.prod.yml logs --tail=200 llm-redteam
```

The service should normally run with `REDTEAM_ENFORCEMENT_MODE=shadow`.
If false positives increase, keep it in shadow mode and investigate benchmark
drift. Do not switch to blocking merely to suppress alerts.

## Dataset service not ready

```bash
docker compose -f docker-compose.prod.yml logs --tail=200 dataset-poison
```

Common causes:

- `DATASET_BASELINE_FILE` missing on the host
- NPZ does not contain a 2D numeric `features` array
- baseline has too few samples
- feature array contains NaN/inf

The correct recovery is to restore a validated known-clean baseline. Do not
remove the readiness gate and do not let untrusted request traffic create the
initial baseline.

## 502 / 504 from gateway

- 502: upstream connection/protocol failure
- 504: upstream timeout after the configured HTTP client timeout

Use the gateway request ID from a 502 response to correlate logs. Internal
exception text is intentionally not returned to callers.

## Security incident: suspected credential compromise

1. Remove external exposure at ingress/load balancer if necessary.
2. Preserve gateway and affected upstream logs.
3. Rotate the specific compromised credential.
4. Restart only the components that consume that credential.
5. Verify caller-controlled `Authorization`, `Cookie`, and `X-API-Key`
   headers are still stripped at the proxy boundary.
6. Review access during the affected window and document findings.

## Post-incident checks

```bash
pytest tests/test_gateway.py -q
pytest tests/integration/ -q
docker compose -f docker-compose.prod.yml config >/dev/null
```

A green local-stub topology is not proof of product functionality. For release
validation, test the gateway against digest-pinned real product images.
