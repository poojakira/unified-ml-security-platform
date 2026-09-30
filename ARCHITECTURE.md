# Unified ML Security Platform - Architecture

> Current architecture: one authenticated gateway with **four production HTTP service slots**. The local Compose topology uses health-contract stubs for fast routing/topology tests; production Compose requires externally built product images and does not publish the stubs as products.

## Runtime boundary

```text
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
+----+-----+------+-----+
     |     |      | 
     |     |      +------------------------+
     |     +---------------+               |
     v                     v               v
mcp-gateway            llm-redteam    dataset-poison
:8080                  :8000          :8000
/v1/*                   /scan          /score,/batch
     |
     +--------------------------------------+
                                            v
                                  model-privacy service
                                  authenticated HTTP contract
```

The production Docker network is internal-only. Only the gateway publishes a host port.

## Local test topology versus production topology

- `docker-compose.yml` is a **contract-test topology**. Its product containers are local stubs used to validate health, routing, credentials, network boundaries, and failure behavior. Stub success is not evidence that downstream product business logic ran.
- `docker-compose.prod.yml` is a **production deployment contract**. It never builds local product stubs and requires externally supplied product images, preferably digest-pinned.
- Current CI explicitly runs local contract-stub health jobs and integration topology tests, then separately validates the production Compose contract.

## Synchronous service slots

| Prefix | Production upstream slot | Contract |
|---|---|---|
| `/mcp_gateway/*` | MCP gateway image | MCP tool-call/control-plane API |
| `/llm_redteam/*` | LLM red-team HTTP image | Prompt scan API |
| `/dataset_poison/*` | Dataset-poison detector HTTP image | Dataset screening API |
| `/model_privacy/*` | Model-privacy assessment HTTP image | Privacy assessment API |

Unknown prefixes return 404.

## Batch/admission systems

These remain independently releasable and are deliberately not represented as synchronous gateway products:

- `hf-model-provenance-scanner` - model artifact admission / supply-chain scanning.
- `adversarial-ml-lab` - adversarial robustness evaluation.

## Trust boundaries

1. **External caller -> gateway**  
   Authenticated with `GATEWAY_API_KEY`.

2. **Gateway -> backend**  
   Caller `Authorization`, `Cookie`, and `X-API-Key` values are dropped. The gateway injects service-specific credentials.

3. **Dataset detector -> baseline**  
   Production readiness depends on a known-clean baseline and the downstream product contract.

4. **LLM detector -> enforcement**  
   Detection and hard blocking remain separate concerns; downstream product policy owns enforcement semantics.

## Security controls implemented in this integration layer

- external API-key authentication
- distinct per-service upstream credentials
- constant-time external-key comparison
- request-header allowlisting
- body-size limits
- opaque upstream errors with request IDs
- internal-only Docker networking
- non-root gateway image
- readiness-gated startup
- digest-pinnable product-image inputs
- CI lint/type/test/security/integration/compose validation

## Availability and deployment boundary

The repository demonstrates a single-host control-plane contract and CI-validated integration topology. It does **not** establish multi-region HA, production load capacity, centralized observability, global rate limiting, service-mesh mTLS, or a running production deployment.

Local stub tests prove integration contracts only. Product functionality and product-specific security efficacy must be established by each independently released product repository/image.
