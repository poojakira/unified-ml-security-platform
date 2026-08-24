# Unified ML Security Platform — System Architecture

> Version: 1.0.0 | Last updated: 2026-08-24

This document describes the production architecture of the Unified ML Security
Platform, including service topology, data flows, deployment models, and
security boundaries.

---

## 1. High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL BOUNDARY                                  │
│                                                                             │
│   ┌─────────────┐         ┌──────────────────────────────────────────────┐  │
│   │  Clients /  │  HTTPS  │            API Gateway (FastAPI)             │  │
│   │  CI/CD /    │────────►│  - TLS termination (port 8443)              │  │
│   │  Dashboards │         │  - API key authentication                    │  │
│   └─────────────┘         │  - Rate limiting & request routing           │  │
│                           │  - Health: GET /health (unauthenticated)     │  │
│                           │  - Status: GET /status (authenticated)       │  │
│                           └─────────────┬────────────────────────────────┘  │
│                                         │                                   │
└─────────────────────────────────────────┼───────────────────────────────────┘
                                          │ mlsec-internal network (bridge)
┌─────────────────────────────────────────┼───────────────────────────────────┐
│                        INTERNAL SERVICE MESH                                 │
│                                         │                                   │
│    ┌────────────────────────────────────┼────────────────────────────┐      │
│    │                                    ▼                            │      │
│    │  ┌──────────────┐  ┌──────────────────────┐  ┌─────────────┐  │      │
│    │  │ HF Scanner   │  │  MCP Security        │  │ Adversarial │  │      │
│    │  │ (Port 8001)  │  │  Gateway (Port 8002) │  │ ML Lab      │  │      │
│    │  │              │  │                      │  │ (Port 8003) │  │      │
│    │  │ Model supply │  │ Agent tool-call      │  │ Robustness  │  │      │
│    │  │ chain scans  │  │ monitoring &         │  │ evaluation  │  │      │
│    │  │ & provenance │  │ detection            │  │ & attacks   │  │      │
│    │  └──────────────┘  └──────────────────────┘  └─────────────┘  │      │
│    │                                                                │      │
│    │  ┌──────────────┐  ┌──────────────────────┐  ┌─────────────┐  │      │
│    │  │ LLM Redteam  │  │  Dataset Poisoning   │  │ Model       │  │      │
│    │  │ (Port 8004)  │  │  Detector (Port 8005)│  │ Privacy     │  │      │
│    │  │              │  │                      │  │ (Port 8006) │  │      │
│    │  │ Prompt-based │  │ Training data        │  │ Membership  │  │      │
│    │  │ red-teaming  │  │ integrity            │  │ inference & │  │      │
│    │  │ & jailbreak  │  │ verification         │  │ extraction  │  │      │
│    │  └──────────────┘  └──────────────────────┘  └─────────────┘  │      │
│    │                                                                │      │
│    │  ┌──────────────────────────────────────────────────────────┐  │      │
│    │  │  PulseNet RUL Forecasting (Port 8007) [ARCHIVED]         │  │      │
│    │  │  Predictive maintenance — not part of active deployment  │  │      │
│    │  └──────────────────────────────────────────────────────────┘  │      │
│    └────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│    ┌────────────────────────────────────────────────────────────────┐      │
│    │                    SHARED INFRASTRUCTURE                        │      │
│    │  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐  │      │
│    │  │ ATT&CK v19  │  │ Benchmark    │  │ Security Dashboard   │  │      │
│    │  │ Detector    │  │ Measurement  │  │ (static HTML)        │  │      │
│    │  │ Engine      │  │ Service      │  │                      │  │      │
│    │  └─────────────┘  └──────────────┘  └──────────────────────┘  │      │
│    └────────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Service Inventory

| Service | Port | Route Prefix | Repository | Status |
|---------|------|-------------|------------|--------|
| API Gateway | 8000/8443 | `/` | (this repo) | Active |
| HF Scanner | 8001 | `/hf_scanner/` | `poojakira/hf-model-provenance-scanner` | Active |
| MCP Gateway | 8002 | `/mcp_gateway/` | `poojakira/mcp-agent-security-gateway` | Active |
| Adversarial ML | 8003 | `/adv_ml/` | `poojakira/adversarial-ml-lab` | Active |
| LLM Redteam | 8004 | `/llm_redteam/` | `poojakira/llm-redteam-framework` | Active |
| Dataset Poison | 8005 | `/dataset_poison/` | `poojakira/dataset-poisoning-detector` | Active |
| Model Privacy | 8006 | `/model_privacy/` | `poojakira/model-privacy-attacks` | Active |
| PulseNet | 8007 | `/pulsenet/` | `poojakira/PulseNet-RUL-Forecasting` | Archived |

---

## 3. Data Flow

### 3.1 Request Lifecycle

```
Client ──► Gateway ──► Target Service ──► Response ──► Gateway ──► Client
  │           │                                           │
  │           ├── Auth check (X-API-Key header)           │
  │           ├── Service routing (path prefix)           │
  │           └── Timeout enforcement (30s)               │
  │                                                       │
  └──── Error: 401 / 404 / 502 / 504 ◄──────────────────┘
```

### 3.2 Security Scanning Pipeline

```
┌───────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│ Model Artifact│     │  HF Scanner      │     │  ATT&CK v19         │
│ (HuggingFace, │────►│  - Provenance    │────►│  Detector Engine     │
│  S3, local)   │     │  - Format check  │     │  - Rule matching     │
└───────────────┘     │  - Signature     │     │  - Technique chain   │
                      └──────────────────┘     │  - Confidence score  │
                                               └──────────┬──────────┘
                                                          │
                                                          ▼
                      ┌──────────────────┐     ┌─────────────────────┐
                      │  Dashboard       │◄────│  Findings Report     │
                      │  (index.html)    │     │  - SARIF/JSON        │
                      └──────────────────┘     │  - Recommended acts  │
                                               └─────────────────────┘
```

### 3.3 Red-Teaming & Robustness Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ Attack Config   │────►│  Adversarial ML  │────►│  Benchmark        │
│ (FGSM, PGD,    │     │  Lab             │     │  Measurement      │
│  C&W, etc.)    │     │  - Attack exec   │     │  - Portfolio score │
└─────────────────┘     │  - Robustness    │     │  - Coverage map   │
                        └──────────────────┘     └──────────────────┘
                                                          │
┌─────────────────┐     ┌──────────────────┐              │
│ Prompt Batch    │────►│  LLM Redteam     │──────────────┘
│ (jailbreak,     │     │  Framework       │
│  injection)    │     │  - Detection     │
└─────────────────┘     └──────────────────┘
```

### 3.4 Data Integrity Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ Training Data   │────►│  Dataset Poison  │────►│  Anomaly Findings │
│ (batched input) │     │  Detector        │     │  - Statistical    │
└─────────────────┘     │  - Statistical   │     │  - Label-flip     │
                        │    analysis      │     │  - Backdoor       │
                        └──────────────────┘     └──────────────────┘

┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ Target Model    │────►│  Model Privacy   │────►│  Privacy Risk     │
│                 │     │  Attacks         │     │  Report           │
└─────────────────┘     │  - MIA           │     │  - Leakage score  │
                        │  - Model extract │     │  - Mitigations    │
                        └──────────────────┘     └──────────────────┘
```

---

## 4. Deployment Topology

### 4.1 Docker Compose (Development & CI)

```yaml
# docker-compose.yml — development with hot reload
# docker-compose.prod.yml — production hardened
```

Production compose (`docker-compose.prod.yml`) characteristics:
- **Internal network only**: `mlsec-internal` bridge with `internal: true`
- **Single ingress**: Only the gateway exposes ports (8000, 8443)
- **Resource limits**: CPU and memory constraints per service
- **Health checks**: Gateway has a 30s-interval HTTP health check
- **Fail-fast secrets**: `API_KEY` is required (`${API_KEY:?}` syntax)
- **Restart policy**: `unless-stopped` for all services

### 4.2 Kubernetes (Production Target)

```
┌─────────────────────────────────────────────────────┐
│  Namespace: mlsec-platform                          │
│                                                     │
│  ┌───────────────────┐                              │
│  │ Ingress Controller│  TLS termination             │
│  │ (NGINX/ALB)       │  + rate limiting             │
│  └────────┬──────────┘                              │
│           │                                         │
│  ┌────────▼──────────┐                              │
│  │ Service: gateway  │  ClusterIP                   │
│  │ Deployment: 2 rep │  HPA: 2-10 pods             │
│  └────────┬──────────┘                              │
│           │                                         │
│  ┌────────▼──────────────────────────────────────┐  │
│  │ Services (ClusterIP, internal only)           │  │
│  │                                               │  │
│  │  hf-scanner    mcp-gateway    adv-ml          │  │
│  │  llm-redteam   dataset-poison model-privacy   │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │ NetworkPolicy: deny-all-ingress               │  │
│  │ Allow: gateway → product services (ports)     │  │
│  │ Allow: product services → (none, egress only) │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │ Secrets (sealed-secrets or external-secrets)  │  │
│  │  - API_KEY                                    │  │
│  │  - PULSENET_JWT_SECRET                        │  │
│  │  - COSIGN_PRIVATE_KEY                         │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 4.3 CI/CD Pipeline Stages

```
  lint-and-typecheck ──► unit-tests ──► product-health-tests
         │                    │                   │
         ▼                    ▼                   │
  security-scan ◄────── integration-tests ◄──────┘
         │                    │
         ▼                    ▼
  build-and-push ──► validate-deployment-plan ──► release
```

---

## 5. Security Boundaries

### 5.1 Network Segmentation

| Zone | Description | Access Rules |
|------|-------------|--------------|
| External | Public internet / CI clients | HTTPS only to gateway port 8443 |
| DMZ | Gateway container | Accepts external, routes to internal |
| Internal | Product service containers | No external access; gateway-only ingress |

### 5.2 Authentication & Authorization

- **Gateway-level**: All requests (except `/health`) require `X-API-Key` header
- **Key requirements**: Minimum 32 characters, validated at startup
- **Service-to-service**: Services trust traffic from the internal network
- **PulseNet**: Additional JWT-based auth (`PULSENET_JWT_SECRET`)

### 5.3 Secrets Management

| Secret | Scope | Rotation Policy |
|--------|-------|-----------------|
| `API_KEY` | Gateway + all services | 90-day rotation |
| `PULSENET_JWT_SECRET` | PulseNet only | 90-day rotation |
| `COSIGN_PRIVATE_KEY` | CI/CD image signing | Annual rotation |
| `GITHUB_TOKEN` | CI/CD registry push | Auto (workflow) |

### 5.4 Supply Chain Security

- **Image signing**: Cosign attestation on all published images
- **SBOM generation**: Syft produces SPDX-JSON for each build
- **Vulnerability scanning**: Trivy (filesystem) + Grype (container)
- **Dependency audit**: Safety for Python deps, Dependabot for automated PRs
- **Bandit**: Static analysis for Python security anti-patterns

### 5.5 Defense-in-Depth Layers

```
Layer 1: TLS termination (external boundary)
Layer 2: API key authentication (gateway)
Layer 3: Network isolation (internal bridge / NetworkPolicy)
Layer 4: Resource limits (DoS protection)
Layer 5: Input validation (per-service)
Layer 6: ATT&CK detection engine (behavioral analysis)
Layer 7: Audit logging (structured, no PII leakage)
```

---

## 6. ATT&CK v19 Detection Architecture

The platform embeds a MITRE ATT&CK v19 detection contract that covers:

- **Enterprise**: 15 tactics (TA0043 through TA0040)
- **Mobile**: 12 tactics
- **ICS**: 12 tactics

Detection rules are defined as `DetectionRule` dataclasses with:
- Matrix/tactic/technique/sub-technique identifiers
- Confidence levels (High/Medium)
- Regex-based pattern matching
- Recommended response actions

Output conforms to the `AnalysisResult` TypedDict contract, supporting both
JSON and human-readable text formats.

---

## 7. Health Check Contract

Every service must implement:

```json
GET /health → 200 OK
{
  "status": "ok",
  "product": "<service_name>",
  "port": <port_number>
}
```

The gateway health endpoint returns:

```json
GET /health → 200 OK
{
  "status": "healthy",
  "version": "1.0.0"
}
```

Health checks are:
- **Unauthenticated** (for load balancer probes)
- **Lightweight** (no downstream calls)
- **Deterministic** (always return immediately)

---

## 8. Error Handling

| HTTP Code | Meaning | Source |
|-----------|---------|--------|
| 401 | Missing or invalid API key | Gateway auth |
| 404 | Unknown service in path | Gateway routing |
| 502 | Upstream service error | Gateway proxy |
| 503 | Service not bundled | Gateway stubs |
| 504 | Service timeout (>30s) | Gateway proxy |

Error responses never expose internal exception details. A `request_id` is
returned for correlation with server-side logs.

---

## 9. Observability

- **Structured logging**: JSON format with request IDs
- **Health endpoints**: Load-balancer and orchestrator integration
- **Coverage reporting**: pytest-cov with 25% minimum threshold
- **SARIF upload**: Security findings visible in GitHub Security tab
- **Artifact preservation**: Integration test logs uploaded on failure

---

## 10. Non-Goals & Boundaries

This repository is an **integration workspace**, not a monolith:

- Service implementations live in their own repositories
- Product containers in this repo are architecture-spec stubs
- No runnable ML inference happens in this repo
- No measured detection claims are made from stubs alone
- PulseNet is archived and excluded from active deployment

---

## 11. Future Architecture Targets

1. **Event bus**: AsyncAPI-based event mesh for cross-service notifications
2. **Service mesh**: Istio/Linkerd for mTLS between services
3. **Distributed tracing**: OpenTelemetry spans across gateway and products
4. **Policy engine**: OPA/Gatekeeper for fine-grained access control
5. **Multi-tenant isolation**: Per-customer namespace separation

---

## Appendix A: Port Assignments

| Port | Service | Protocol |
|------|---------|----------|
| 8000 | Gateway (HTTP) | HTTP/1.1 |
| 8443 | Gateway (HTTPS) | TLS 1.3 |
| 8001 | HF Scanner | HTTP/1.1 |
| 8002 | MCP Gateway | HTTP/1.1 |
| 8003 | Adversarial ML | HTTP/1.1 |
| 8004 | LLM Redteam | HTTP/1.1 |
| 8005 | Dataset Poison | HTTP/1.1 |
| 8006 | Model Privacy | HTTP/1.1 |
| 8007 | PulseNet (archived) | HTTP/1.1 |

## Appendix B: Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_KEY` | Yes | — | Gateway authentication key (≥32 chars) |
| `PULSENET_JWT_SECRET` | PulseNet only | — | JWT signing secret for PulseNet |
| `LOG_LEVEL` | No | `INFO` | Gateway log verbosity |
| `SERVICE_NAME` | No | `ml-security-spec-service` | Spec service identifier |
| `PORT` | No | `8000` | Spec service listen port |
