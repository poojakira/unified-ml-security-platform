# Integration Guide — Adding New Security Services

> Audience: Engineers integrating a new ML security service into the platform.

This guide covers the requirements, contracts, and patterns for adding a new
product service to the Unified ML Security Platform.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Service Registration](#2-service-registration)
3. [Health Check Requirements](#3-health-check-requirements)
4. [API Contracts](#4-api-contracts)
5. [Event Bus Patterns](#5-event-bus-patterns)
6. [Docker Integration](#6-docker-integration)
7. [CI/CD Integration](#7-cicd-integration)
8. [Security Checklist](#8-security-checklist)
9. [Testing Requirements](#9-testing-requirements)

---

## 1. Prerequisites

Before integrating a new service, ensure you have:

- [ ] A standalone repository with its own test suite
- [ ] A `Dockerfile` that builds a minimal production image
- [ ] A `/health` endpoint returning the standard contract
- [ ] An `API_KEY` environment variable for authentication
- [ ] Python 3.11+ (platform standard)
- [ ] FastAPI as the HTTP framework (recommended, not required)

---

## 2. Service Registration

### 2.1 Gateway Configuration

Add your service to the `SERVICES` dictionary in `gateway_server.py`:

```python
SERVICES = {
    # ... existing services ...
    "your_service": "http://your-service:8010",
}
```

### 2.2 Port Assignment

Request a port from the platform maintainers. Current assignments:

| Range | Purpose |
|-------|---------|
| 8000 | Gateway |
| 8001–8006 | Active product services |
| 8007 | Reserved (archived PulseNet) |
| 8008–8099 | Available for new services |

### 2.3 Docker Compose Entry

Add your service to both `docker-compose.yml` and `docker-compose.prod.yml`:

```yaml
  your-service:
    build:
      context: .
      dockerfile: products/your_service/Dockerfile
    environment:
      - API_KEY=${API_KEY:?API_KEY is required}
    networks:
      - mlsec-internal
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
    restart: unless-stopped
```

### 2.4 Product Directory Structure

Create your product directory under `products/`:

```
products/your_service/
├── __init__.py
├── Dockerfile
├── README.md
├── requirements.txt
├── server.py
└── tests/
    ├── __init__.py
    └── test_health.py
```

---

## 3. Health Check Requirements

### 3.1 Endpoint Contract

Every service **must** implement an unauthenticated health endpoint:

```
GET /health HTTP/1.1

Response: 200 OK
Content-Type: application/json

{
  "status": "healthy",
  "product": "<service_name>"
}
```

### 3.2 Implementation Rules

| Rule | Requirement |
|------|-------------|
| Authentication | None (unauthenticated for load balancer probes) |
| Latency | < 100ms response time |
| Dependencies | Must not call downstream services |
| Failure mode | Return 503 if service is degraded |
| Readiness vs liveness | `/health` serves as both; separate if needed |

### 3.3 Reference Implementation

```python
from fastapi import FastAPI

app = FastAPI(title="your_service", version="1.0.0")

@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "product": "your_service"}
```

### 3.4 Docker Health Check

Add to your compose service definition:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8010/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 15s
```

---

## 4. API Contracts

### 4.1 Request Format

All service endpoints (except `/health`) must:

- Accept `Content-Type: application/json`
- Validate the `X-API-Key` header (or delegate to gateway)
- Return structured JSON responses
- Include appropriate HTTP status codes

### 4.2 Standard Response Envelope

```json
{
  "status": "success" | "error",
  "data": { ... },
  "metadata": {
    "service": "your_service",
    "version": "1.0.0",
    "request_id": "abc123",
    "timestamp": "2026-08-24T12:00:00Z"
  }
}
```

### 4.3 Error Response Format

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description",
    "details": {}
  },
  "metadata": { ... }
}
```

**Security rule**: Never expose stack traces, internal paths, or exception
details in error responses. Use request IDs for correlation.

### 4.4 Common Input Patterns by Service Type

| Service Type | Input Contract | Output Contract |
|-------------|---------------|-----------------|
| Scanner | `{"artifact_path": "...", "options": {}}` | `{"findings": [...], "total_findings": N}` |
| Detector | `{"samples": [...], "config": {}}` | `{"anomalies": [...], "score": 0.0-1.0}` |
| Red-team | `{"prompts": [...], "target": "..."}` | `{"results": [...], "success_rate": 0.0-1.0}` |
| Privacy | `{"model_ref": "...", "attack_type": "..."}` | `{"risk_score": 0.0-1.0, "mitigations": [...]}` |

### 4.5 Gateway Routing

The gateway proxies requests based on the first path segment:

```
POST /your_service/scan  →  http://your-service:8010/scan
GET  /your_service/results/123  →  http://your-service:8010/results/123
```

Supported methods: `GET`, `POST`, `PUT`, `DELETE`, `PATCH`

Timeout: 30 seconds (configurable per service in future versions)

---

## 5. Event Bus Patterns

### 5.1 Current Architecture (Synchronous)

The platform currently uses synchronous HTTP request/response. Each service is
independently callable through the gateway.

### 5.2 Future Event Bus (Planned)

The target architecture includes an async event bus for:

- Cross-service notifications (scan complete → trigger analysis)
- Audit event streaming
- Aggregate reporting

### 5.3 Event Schema (Target)

```json
{
  "event_id": "uuid",
  "event_type": "scan.completed | detection.triggered | alert.raised",
  "source": "service_name",
  "timestamp": "ISO-8601",
  "payload": { ... },
  "correlation_id": "request-uuid"
}
```

### 5.4 Integration Pattern: Scan → Detect → Alert

```
1. Client submits artifact to HF Scanner
2. HF Scanner publishes: scan.completed {findings: [...]}
3. ATT&CK Detector subscribes, runs analysis
4. ATT&CK Detector publishes: detection.triggered {techniques: [...]}
5. Dashboard subscribes, updates visualization
```

### 5.5 Preparing for Event Bus

To make your service event-bus-ready:

1. **Emit structured events** — Log key actions as JSON events
2. **Idempotent handlers** — Design endpoints to handle duplicate delivery
3. **Correlation IDs** — Pass and propagate `X-Request-ID` headers
4. **Async-ready** — Use `async def` for handlers (FastAPI default)

---

## 6. Docker Integration

### 6.1 Dockerfile Requirements

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install deps first (layer caching)
COPY products/your_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY products/your_service/ .

# Non-root user
RUN useradd -r -s /bin/false appuser
USER appuser

EXPOSE 8010

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8010"]
```

### 6.2 Image Requirements

| Requirement | Standard |
|-------------|----------|
| Base image | `python:3.12-slim` |
| User | Non-root (`appuser`) |
| Size target | < 500MB |
| Secrets | Environment variables only, never baked in |
| Labels | OCI standard labels recommended |

### 6.3 Network Rules

- Services connect **only** to `mlsec-internal` network
- Network is `internal: true` — no direct external access
- All external traffic routes through the gateway
- Service-to-service calls are allowed within the mesh

---

## 7. CI/CD Integration

### 7.1 Add to Product Health Tests

Update `.github/workflows/ci.yml` matrix:

```yaml
product-health-tests:
  strategy:
    matrix:
      product: [hf_scanner, mcp_gateway, adv_ml, llm_redteam, dataset_poison, model_privacy, your_service]
```

### 7.2 Add to pyproject.toml

Register your package and test paths:

```toml
[tool.setuptools]
packages = [..., "products.your_service"]

[tool.pytest.ini_options]
testpaths = [..., "products/your_service/tests"]
```

### 7.3 Coverage Requirements

| Level | Threshold | Scope |
|-------|-----------|-------|
| Unit tests | 60% minimum | Per-product |
| Integration | 25% minimum | Platform-wide |

### 7.4 Security Scanning

Your code will automatically be scanned by:
- **Ruff** — Linting and formatting
- **Bandit** — Python security issues (HIGH/MEDIUM = blocking)
- **Trivy** — Vulnerability scanning
- **Grype** — Container vulnerability scanning
- **Safety** — Dependency CVE checks
- **Dependabot** — Automated dependency updates

---

## 8. Security Checklist

Before submitting your integration PR, verify:

- [ ] `/health` endpoint requires no authentication
- [ ] All other endpoints validate `X-API-Key` or trust gateway auth
- [ ] No secrets hardcoded in source or Dockerfile
- [ ] No `B104` warnings (binding to 0.0.0.0 is acceptable with `# nosec`)
- [ ] Error responses don't leak internal details
- [ ] Input validation on all user-provided data
- [ ] Resource limits defined in compose files
- [ ] Dependencies pinned to exact versions in `requirements.txt`
- [ ] No `eval()`, `pickle.loads()`, or `subprocess` with user input
- [ ] Passes `bandit -r . -ll` with no HIGH/MEDIUM findings

---

## 9. Testing Requirements

### 9.1 Required Test: Health Endpoint

Every product must have at minimum:

```python
# products/your_service/tests/test_health.py
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MLSEC_API_KEY", "test-key-for-ci")
    from products.your_service.server import app
    return TestClient(app)

def test_health_returns_healthy(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["product"] == "your_service"
```

### 9.2 Integration Test Participation

If your service interacts with others, add a test in `tests/integration/`:

```python
# tests/integration/test_your_service.py
def test_your_service_reachable(client):
    """Service responds through the gateway."""
    response = client.get(
        "/your_service/health",
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 200
```

### 9.3 Running Tests Locally

```bash
# Install dev dependencies
pip install -e .[dev]

# Run your product tests
pytest products/your_service/tests/ -v

# Run full platform tests
pytest tests/ -v

# Run integration tests (requires Docker)
docker compose -f docker-compose.prod.yml up -d
pytest tests/integration/ -v
```

---

## Quick Reference: Integration Checklist

```
□ Create products/your_service/ directory structure
□ Implement /health endpoint
□ Write Dockerfile
□ Add to gateway SERVICES dict
□ Add to docker-compose.yml and docker-compose.prod.yml
□ Add to CI matrix in .github/workflows/ci.yml
□ Add to pyproject.toml (packages + testpaths)
□ Write health check test (60% coverage minimum)
□ Pass security checklist
□ Submit PR with integration test proof
```
