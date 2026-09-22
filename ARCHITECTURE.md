# Unified ML Security Platform — Architecture

> Current architecture: synchronous control plane for three real HTTP products,
> plus separate batch/admission security jobs.

## Runtime boundary

```
External caller
     |
     | X-API-Key
     v
+-----------------------+
| FastAPI Gateway :8000 |
| - caller auth         |
| - header allowlist    |
| - body-size limit     |
| - timeout/error map   |
+----+-----------+------+
     |           |
     |           +-----------------------------+
     |                                         |
     v                                         v
mcp-gateway:8080                        llm-redteam:8000
/v1/*                                   /scan
runtime enforcement                     shadow by default
     |
     +-----------------------------------------+
                                               |
                                               v
                                      dataset-poison:8000
                                      /score, /batch
                                      trusted baseline required
```

The production Docker network is internal-only. Only the gateway publishes a
host port.

## Batch/admission systems

These are independently releasable security tools, but are deliberately not
pretended to be long-running gateway microservices:

- `hf-model-provenance-scanner` — model artifact admission / supply-chain scan
- `adversarial-ml-lab` — adversarial robustness evaluation job
- `model-privacy-attacks` — privacy assessment job

They should run in CI, release pipelines, or scheduled assessment jobs and
produce evidence consumed by humans or policy automation.

## Trust boundaries

1. **External caller -> gateway**  
   Authenticated with `GATEWAY_API_KEY`.

2. **Gateway -> backend**  
   Caller `Authorization`, `Cookie`, and `X-API-Key` values are dropped.
   The gateway injects a service-specific credential.

3. **Dataset detector -> baseline**  
   The detector does not learn an initial baseline from request traffic.
   A known-clean NPZ is mounted read-only and readiness fails until loaded.

4. **LLM detector -> enforcement**  
   Detection and enforcement are separate. The service defaults to shadow mode
   because current OOD evidence shows substantial false-positive cost.

## Routing table

| Prefix | Upstream | Contract |
|---|---|---|
| `/mcp_gateway/*` | `http://mcp-gateway:8080/*` | MCP control plane |
| `/llm_redteam/*` | `http://llm-redteam:8000/*` | Prompt scan API |
| `/dataset_poison/*` | `http://dataset-poison:8000/*` | Dataset screening API |

Unknown prefixes return 404.

## Availability model

The repository currently demonstrates a single-host Compose deployment, not
multi-region HA. The gateway uses a shared async HTTP client with a 30-second
upstream timeout. There is no distributed circuit breaker, global rate limiter,
service mesh, or automatic failover in this repository.

## Security controls implemented here

- distinct external and service credentials
- constant-time external key comparison
- explicit request-header allowlist
- proxy body-size ceiling
- opaque upstream error responses with request IDs
- internal-only Docker bridge
- non-root gateway image
- readiness-gated backend startup
- security/lint/test/container CI gates
- digest-pinnable product image inputs

## Deliberate non-claims

This repository does **not** prove:

- multi-region or multi-host availability
- production load capacity
- centralized logging/alerting
- enterprise secrets-manager integration
- service-mesh mTLS
- real-time HTTP interfaces for the batch security projects

Those require deployment-specific evidence outside this repository.
