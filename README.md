# Unified ML Security Platform

A Docker Compose integration workspace that orchestrates 7 ML security microservices behind a FastAPI gateway, providing compose validation, health checks, resource limits, CI/CD pipelines, and a shared MITRE ATT&CK v19 detection module.

## The Core Problem

You have built separate tools for model scanning, adversarial testing, dataset poisoning detection, LLM red-teaming, and privacy attacks. Each lives in its own repository with its own deployment story. A security analyst now asks: "Can I scan a model for supply chain backdoors, run adversarial robustness tests, and check for membership inference vulnerabilities from one authenticated endpoint?" Without an integration layer, the answer involves stitching together 7 different APIs, managing 7 sets of credentials, and hoping no service falls over silently.

This repository is that integration layer. It defines how the services compose, what their health contracts look like, how traffic routes between them, and what CI must pass before anything ships.

## Executive Summary

This platform is for ML security engineers and platform teams who operate multiple ML security tools and need them to work together as a single, observable system. It solves the problem of multi-service orchestration for ML security: instead of deploying and monitoring each tool independently, this workspace provides a single gateway, a unified authentication model, shared network isolation, resource governance, and a common threat detection contract based on MITRE ATT&CK v19.

The platform composes services from 7 independent repositories into a validated, tested, deployable unit. Each product service owns its own logic, tests, and dependencies. This repo owns the integration contracts, the gateway routing, the CI validation, and the shared detection taxonomy.

## Why This Repository Exists

ML security is not a single tool. Scanning models for pickle RCE is different from testing adversarial robustness, which is different from detecting dataset poisoning. Each concern lives in a separate codebase because they have different dependencies, different expertise requirements, and different update cadences.

But operators need them to behave as one system. This repository exists to answer:

- How do 7 independent ML security services talk to each other and to the outside world?
- What is the minimum viable contract each service must satisfy to participate in the platform?
- How do you validate that all services start, respond to health checks, and stay within resource limits before deploying?
- How do you enforce network isolation so internal services never expose themselves directly?
- What shared threat taxonomy do all services report against?
- How do you run security scans (Bandit, Trivy, Grype, Safety) and integration tests in CI before merging?

## Architecture Overview

```
                         ┌─────────────────┐
                         │     Gateway     │ :8000 (HTTP) / :8443 (HTTPS)
                         │  (FastAPI Proxy) │
                         └────────┬────────┘
                                  │  API Key Auth (X-API-Key header)
        ┌─────────┬─────────┬─────┼─────┬──────────┬──────────┬──────────┐
        │         │         │     │     │          │          │          │
        ▼         ▼         ▼     ▼     ▼          ▼          ▼          ▼
   hf-scanner  mcp-gw   adv-ml  llm-  dataset-   model-    pulsenet   attacks/
    :8001      :8002     :8003  redteam poison    privacy    :8007     (shared
                                :8004   :8005     :8006                module)
        │         │         │     │     │          │          │
        └─────────┴─────────┴─────┴─────┴──────────┴──────────┴──────────┘
                     mlsec-internal (bridge network, internal: true)
                              No external egress
```

### Component Responsibilities

| Component | Role | Source Repository |
|-----------|------|-------------------|
| Gateway | Reverse proxy, API key authentication, request routing, health endpoint | This repo (`gateway_server.py`) |
| hf-scanner | Model supply chain scanning (pickle RCE, typosquatting, metadata injection) | `poojakira/hf-model-provenance-scanner` |
| mcp-gateway | MCP agent security monitoring (BCC exfil, credential harvest, prompt injection) | `poojakira/mcp-agent-security-gateway` |
| adv-ml | Adversarial robustness evaluation (FGSM, PGD, C&W, AutoAttack, certified) | `poojakira/adversarial-ml-lab` |
| llm-redteam | LLM red-team testing (prompt injection, encoding evasion, exfiltration) | `poojakira/llm-redteam-framework` |
| dataset-poison | Dataset poisoning detection (clean-label, distributed, label flip, drift) | `poojakira/dataset-poisoning-detector` |
| model-privacy | Privacy attack evaluation (membership inference, model extraction, Min-K%) | `poojakira/model-privacy-attacks` |
| pulsenet | Remaining Useful Life forecasting with FDIA detection | `poojakira/PulseNet-RUL-Forecasting` |
| attacks/ | Shared ATT&CK v19 detection module, attack catalog (78 attacks across 7 products) | This repo |

## End-to-End Workflow

1. **Gateway receives request**: An operator sends an authenticated request (e.g., `POST /hf_scanner/scan`) with an `X-API-Key` header to the gateway on port 8000.

2. **Authentication check**: The gateway validates the API key (minimum 32 characters). Unauthenticated requests get a 401. The `/health` endpoint is the only unauthenticated route (for load balancer probes).

3. **Routing**: The gateway extracts the service name from the URL path, looks up the internal Docker network address, and proxies the request using `httpx.AsyncClient` with a 30-second timeout.

4. **Service processing**: The target service (e.g., `hf-scanner` at `http://hf-scanner:8001`) processes the request using its own logic and dependencies.

5. **Response relay**: The gateway returns the service response to the caller. On timeout, it returns 504. On upstream errors, it returns 502 with an opaque request ID (no internal details leaked).

6. **Shared detection contract**: Any service can use the `attacks/attack_v19_detector.py` module to classify findings against MITRE ATT&CK v19 (Enterprise, Mobile, ICS matrices). The detector uses regex-based pattern matching with 22 seed rules and returns structured detections with tactic, technique, sub-technique, confidence, evidence, and recommended actions.

7. **CI validation**: On every push, GitHub Actions runs lint (Ruff), type checking (Pyright), unit tests (pytest with coverage), product health tests (per-service at 60% coverage threshold), integration tests (full docker-compose build and health check), and security scans (Bandit, Safety, Trivy, Grype).

## Design Decisions and Trade-offs

**Stub services instead of vendored code**: Product services are built from per-product Dockerfiles in `products/`, but this repo does not vendor the full implementation of each product. The `spec_service.py` provides a minimal HTTP server that responds to `/health` with status "ok" and returns 501 for all other routes. This means the integration tests validate that services start and respond, but do not test business logic. The trade-off: you can validate the compose topology without needing all 7 repos checked out, but you cannot run end-to-end functional tests from this repo alone.

**Internal bridge network with no egress**: All services sit on `mlsec-internal` with `internal: true`. Only the gateway exposes ports 8000 and 8443. This prevents any compromised service from reaching the internet directly, but it means services cannot fetch external resources (like model registries) without explicit proxy configuration.

**Single API key for all services**: Every service receives the same `$API_KEY` environment variable. This simplifies deployment but means service-to-service authentication is flat. A compromised service key compromises all services. The alternative (per-service keys with mTLS) was traded for deployment simplicity at this stage.

**Coverage threshold at 25% (unit) and 60% (product)**: The repository is primarily an integration spec, not a product implementation. The 25% overall threshold reflects that much of the code is stubs. Individual product test directories are held to 60%.

**Pulsenet is present but archived**: The compose file includes pulsenet, and the attack catalog defines attacks for it, but the CI pipeline excludes it from health tests and the gateway code comments it out of active routing. It remains in compose for completeness but is not deployed as an active service.

**Regex-based ATT&CK detection (not ML-based)**: The shared detector uses simple regex patterns, not trained models. This makes it deterministic, dependency-free, and fast, but it will miss obfuscated or novel attack patterns. It is explicitly described as "seed rules" meant to be extended.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Gateway framework | FastAPI 0.111+, Uvicorn 0.30+ |
| HTTP client | httpx 0.27+ |
| Container runtime | Docker 20.10+, Docker Compose v2 |
| CI/CD | GitHub Actions |
| Linting | Ruff 0.8+ |
| Type checking | Pyright 1.1+ |
| Testing | pytest 8.2+, pytest-cov, pytest-asyncio |
| Security scanning | Bandit, Safety/pip-audit, Trivy, Grype |
| SBOM | Syft (SPDX JSON) |
| Image signing | Cosign (Sigstore) |
| Container registry | GitHub Container Registry (ghcr.io) |
| Base image | python:3.12-slim (multi-stage build) |

## Installation and Quick Start

### Prerequisites

- Docker 20.10+ and Docker Compose v2
- Python 3.11+ (for local development)
- 8 GB RAM minimum (16 GB recommended for all services)
- Ports 8000-8010 available

### Production Deployment

```bash
# Clone the repository
git clone https://github.com/poojakira/unified-ml-security-platform.git
cd unified-ml-security-platform

# Set required environment variables
export API_KEY="your-api-key-minimum-32-characters-long"
export PULSENET_JWT_SECRET="your-pulsenet-jwt-secret-min-32-chars"

# Build and start all services
docker compose -f docker-compose.prod.yml up --build -d

# Verify the gateway is healthy
curl http://localhost:8000/health
# {"status":"healthy","version":"1.0.0"}

# Check authenticated service status
curl -H "X-API-Key: $API_KEY" http://localhost:8000/status
# {"status":"operational","services":["adv_ml","dataset_poison","hf_scanner","llm_redteam","mcp_gateway","model_privacy"],"total":6}
```

### Local Development

```bash
# Create and activate virtual environment
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run the full verification suite
make verify  # lint + test + build + security
```

### Usage Examples

```bash
# Route a request to the HF model scanner
curl -X POST http://localhost:8000/hf_scanner/scan \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model_id": "suspicious-org/model-name"}'

# Route a request to the adversarial ML lab
curl -X POST http://localhost:8000/adv_ml/eval/attack \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"attack": "pgd", "eps": 0.031, "steps": 20}'

# Run the ATT&CK v19 detector on a text file
python -m attacks.attack_v19_detector suspicious_log.txt --format json

# Run detector from stdin
echo "PowerShell -EncodedCommand detected on host" | python -m attacks.attack_v19_detector --format text
```

### Resource Limits (Production)

| Service | CPU Limit | Memory Limit | Restart Policy |
|---------|-----------|--------------|----------------|
| gateway | 2 cores | 2 GB | unless-stopped |
| hf-scanner | 1 core | 1 GB | unless-stopped |
| mcp-gateway | 1 core | 1 GB | unless-stopped |
| adv-ml | 2 cores | 4 GB | unless-stopped |
| llm-redteam | 1 core | 2 GB | unless-stopped |
| dataset-poison | 1 core | 1 GB | unless-stopped |
| model-privacy | 1 core | 1 GB | unless-stopped |
| pulsenet | 1 core | 1 GB | unless-stopped |

Total: 10 CPU cores, 13 GB memory for the full stack.

## Security Considerations

**Network isolation**: The `mlsec-internal` bridge network is configured with `internal: true`, preventing any container from initiating outbound connections. Only the gateway container binds to host ports.

**Authentication**: All routes except `/health` require a valid `X-API-Key` header. The gateway fails fast on startup if `API_KEY` is unset or shorter than 32 characters.

**Non-root execution**: The gateway Dockerfile creates a dedicated `mlsec` user and group. The application runs as this non-root user.

**Multi-stage build**: The production Dockerfile uses a builder stage for compilation and a minimal runtime stage, reducing the attack surface by excluding build tools from the final image.

**Error opacity**: The gateway does not expose internal exception details to clients. Upstream errors return an opaque `request_id` for server-side correlation.

**CI security gates**: Every merge requires passing Bandit (HIGH/MEDIUM findings fail the build), Safety/pip-audit (known CVEs fail the build), Trivy (filesystem vulnerability scan), and Grype (with medium severity cutoff).

**SBOM generation**: The CI pipeline produces an SPDX JSON SBOM via Syft on every build.

**Image signing**: When Cosign keys are configured, built images are signed via Sigstore.

**Dependabot**: Automated dependency update PRs via `.github/dependabot.yml`.

**Secrets management**: API keys and JWT secrets are passed via environment variables with required-value syntax (`${API_KEY:?}`) in the production compose file. No secrets are hardcoded.

## Evaluation Methods, Results, and Limitations

### Attack Catalog Coverage

The `attacks/attack_catalog.py` defines 78 attack scenarios across 7 products:

| Product | Attack Count | Categories |
|---------|-------------|------------|
| hf-scanner | 16 | Supply chain (pickle RCE, typosquatting, bypass variants) |
| mcp-gateway | 17 | Email exfiltration, semantic evasion, credential harvest, prompt injection, PII leakage |
| adv-ml | 25 | Evasion (white/black-box), model stealing, adaptive, certified, physical, universal |
| llm-redteam | 6 | Prompt injection, encoding evasion, exfiltration |
| dataset-poison | 5 | Clean-label backdoor, distributed, label flip, drift, fingerprinting |
| model-privacy | 4 | Membership inference (direct, shadow, Min-K%), model extraction |
| pulsenet | 5 | FDIA (stealth, sudden, coordinated), replay, sensor dropout |

### ATT&CK v19 Detector

The shared detector covers all three ATT&CK matrices:
- Enterprise: 15 tactics (TA0001 through TA0040)
- Mobile: 12 tactics
- ICS: 12 tactics

It provides 22 seed detection rules with regex patterns, covering techniques from T1566 (Phishing) through T0855 (Unauthorized Command Message).

### Limitations

- **Stub implementations**: Product services in this repo respond with 501 for non-health routes. Full functionality requires deploying from each product's source repository.
- **No measured detection rates**: The detector rules are deterministic pattern matches, not validated against labeled corpora. No precision/recall numbers are claimed.
- **No load testing results**: Resource limits are specified but no throughput benchmarks are published.
- **Single-region**: The compose configuration assumes a single-host deployment. No multi-region or high-availability configuration exists.

## Production Readiness Assessment

**Honest status**: The gateway authenticates requests (API key), routes traffic to the correct backend service based on URL path prefix, and exposes an unauthenticated `/health` endpoint for load balancer probes. All product services respond to `GET /health` with `{"status": "healthy", "service": "<name>"}`. However, **individual product functionality is stub-only** — non-health routes return 501 (not implemented). Full business logic (model scanning, adversarial evaluation, privacy attacks, etc.) requires deploying each product from its own source repository. This platform validates integration topology, not product functionality.

| Criterion | Status | Notes |
|-----------|--------|-------|
| Health checks | ✅ Working | Gateway and all services respond 200 on `/health` |
| API key authentication | ✅ Working | Gateway enforces X-API-Key on all non-health routes |
| Service routing | ✅ Working | Gateway proxies `/{service}/{path}` to correct internal host |
| Product business logic | ❌ Stub only | All non-health routes return 501; full implementations live in separate repos |
| Resource limits | ✅ Configured | CPU and memory limits on all services in prod compose |
| Restart policy | ✅ Configured | `unless-stopped` on all services |
| Non-root container | ✅ Configured | Gateway runs as `mlsec` user |
| Network isolation | ✅ Configured | Internal bridge, no egress |
| CI/CD pipeline | ✅ Working | Lint, type check, test, security scan, build, push |
| Secret management | ⚠️ Partial | Env vars with required syntax, but no vault integration |
| Logging | ⚠️ Partial | Structured error logging in gateway, no centralized aggregation |
| Monitoring/alerting | ❌ Missing | No Prometheus metrics, no alerting rules |
| Multi-host deployment | ❌ Missing | Single docker-compose host only |
| TLS termination | ⚠️ Partial | Port 8443 exposed but TLS cert provisioning not automated |
| Rate limiting | ❌ Missing | No request rate limiting on the gateway |
| Horizontal scaling | ❌ Missing | Single instance per service |
| Backup/recovery | ❌ Missing | No persistent volumes, no backup strategy |
| Incident runbook | ✅ Available | `RUNBOOK.md` with troubleshooting table |

## Roadmap and Future Improvements

Based on the architecture docs and current gaps:

1. **Replace stub services with real implementations**: Pin service versions from each product repo and validate full end-to-end functionality in CI.
2. **Per-service authentication**: Move from shared API key to per-service mTLS or JWT-based auth for defense in depth.
3. **Observability stack**: Add Prometheus metrics export, Grafana dashboards, and structured log aggregation.
4. **Rate limiting and circuit breakers**: Protect the gateway from abuse and prevent cascading failures.
5. **Multi-host deployment**: Provide Kubernetes manifests or ECS task definitions for horizontal scaling.
6. **TLS automation**: Integrate cert-manager or ACME for automated certificate provisioning on port 8443.
7. **ATT&CK detector expansion**: Move beyond seed regex rules to ML-based detection with measured precision/recall.
8. **Staging environment**: The CI has placeholder jobs for staging/production deployment validation that need real manifests.

## References

- [MITRE ATT&CK v19 Framework](https://attack.mitre.org/) (April 28, 2026)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Compose Specification](https://docs.docker.com/compose/compose-file/)
- [Sigstore/Cosign](https://docs.sigstore.dev/)
- [Trivy Security Scanner](https://aquasecurity.github.io/trivy/)
- [Grype Vulnerability Scanner](https://github.com/anchore/grype)

### Related Repositories

| Repository | Role in Platform |
|------------|-----------------|
| [hf-model-provenance-scanner](https://github.com/poojakira/hf-model-provenance-scanner) | Model supply chain scanning |
| [mcp-agent-security-gateway](https://github.com/poojakira/mcp-agent-security-gateway) | MCP agent tool-call monitoring |
| [adversarial-ml-lab](https://github.com/poojakira/adversarial-ml-lab) | Adversarial robustness evaluation |
| [llm-redteam-framework](https://github.com/poojakira/llm-redteam-framework) | LLM prompt injection testing |
| [dataset-poisoning-detector](https://github.com/poojakira/dataset-poisoning-detector) | Dataset integrity verification |
| [model-privacy-attacks](https://github.com/poojakira/model-privacy-attacks) | Privacy attack simulation |
| [PulseNet-RUL-Forecasting](https://github.com/poojakira/PulseNet-RUL-Forecasting) | Secure RUL prediction |

## License and Author

**License**: Apache License 2.0

**Author**: [poojakira](https://github.com/poojakira)

**Documentation site**: [poojakira.github.io/unified-ml-security-platform](https://poojakira.github.io/unified-ml-security-platform/)

## Engineering Lessons

The hardest part of building a multi-service security platform is not writing any individual detector. It is making 7 independent services start together, stay healthy, fail gracefully, and produce results in a common format. This repo taught three things: (1) integration contracts matter more than implementation details at the platform layer; (2) stub services with health checks let you validate topology before implementations exist; and (3) a shared threat taxonomy (ATT&CK v19 in this case) gives every product a common language for reporting findings, even when their internals are completely different.
