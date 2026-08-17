# Runbook: unified-ml-security-platform

## What This Repo Is

This is an **integration test workspace** and architecture specification hub for an ML security product portfolio. It is **not** a deployed microservices platform.

The repo contains:

- **Product stubs** under `products/` — each has a minimal `server.py` (health-check endpoint only) and a `Dockerfile`
- **A gateway server** (`gateway_server.py`) — FastAPI proxy that routes to product services (used in Docker Compose)
- **An ATT&CK v19 detection contract** (`attacks/`) — shared MITRE ATT&CK detection logic
- **Integration and unit tests** — in `tests/` and `products/*/tests/`
- **Docker Compose files** — for building/validating the full service topology
- **Architecture & measurement docs** — in `docs/`

### Products (stubs)

| Directory | Description |
|-----------|-------------|
| `products/adv_ml` | Adversarial ML evaluation |
| `products/dataset_poison` | Dataset poisoning detection |
| `products/hf_scanner` | HuggingFace model scanning |
| `products/llm_redteam` | LLM red-team framework |
| `products/mcp_gateway` | MCP agent security gateway |
| `products/model_privacy` | Model privacy attacks |
| `products/pulsenet` | Predictive maintenance (archived) |

Each product `server.py` exposes only a `/health` endpoint returning `{"status": "ok", "product": "<name>"}`.

---

## Prerequisites

- **Python 3.10+** (3.11+ recommended; 3.12 tested)
- **pip** (bundled with Python)
- **Git**
- **Docker & Docker Compose** (optional — only for container validation)
- **Make** (optional — convenience targets)

---

## Clone

**Windows (PowerShell):**
```powershell
git clone https://github.com/poojakira/unified-ml-security-platform.git
cd unified-ml-security-platform
```

**Linux/macOS:**
```bash
git clone https://github.com/poojakira/unified-ml-security-platform.git
cd unified-ml-security-platform
```

---

## Installation

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Windows (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e ".[dev]"
```

The `[dev]` extra installs: pytest, pytest-cov, pytest-asyncio, httpx, fastapi, uvicorn, ruff, pyright.

---

## Running Tests

Tests live in `tests/` (gateway integration tests, ATT&CK detector tests) and `products/*/tests/`.

### Using pytest directly

```bash
# Run all configured test paths
pytest

# Or explicitly
pytest tests/ products/
```

### Using Make

```bash
make test
```

The pytest configuration in `pyproject.toml` already includes all product test directories and enables coverage reporting with a 25% minimum threshold.

---

## Linting & Formatting

Ruff is configured (via `pyproject.toml`) to check `attacks/attack_v19_detector.py` and `tests/test_attack_v19_detector.py`.

### Lint

```bash
# Direct
ruff check .

# Via Make
make lint
```

### Format

```bash
# Direct
ruff format .

# Via Make
make format
```

---

## Docker Compose

Three compose files exist for different purposes:

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Main service topology (gateway + all product stubs) |
| `docker-compose.prod.yml` | Production variant (requires `API_KEY`) |
| `docker-compose.redteam.yml` | Red-team testing containers (Kali, Wireshark, exfil server) |

### Validate compose syntax

```bash
docker compose config -q
docker compose -f docker-compose.prod.yml config -q
```

### Start services (development)

#### Linux / macOS

```bash
export API_KEY="your-api-key-at-least-32-chars-long"
docker compose up -d
docker compose ps
curl http://localhost:8000/health
```

#### Windows (PowerShell)

```powershell
$env:API_KEY = "your-api-key-at-least-32-chars-long"
docker compose up -d
docker compose ps
Invoke-RestMethod http://localhost:8000/health
```

### Stop services

```bash
docker compose down
```

### Red-team environment (testing only)

```bash
docker compose -f docker-compose.yml -f docker-compose.redteam.yml up -d
```

> **Warning:** The red-team compose file adds Kali Linux, Wireshark, and an exfiltration server. Never use on production networks.

---

## Makefile Targets

```
make install    # pip install requirements + editable install + dev tools
make lint       # ruff check
make format     # ruff format
make test       # pytest tests/ -q
make build      # python -m build (sdist + wheel)
make security   # bandit + pip-audit
make verify     # lint + test + build + security
```

---

## Project Structure (actual)

```
unified-ml-security-platform/
├── .github/workflows/ci.yml   # GitHub Actions CI
├── attacks/                   # ATT&CK v19 detection contract & catalog
├── benchmarks/                # Portfolio measurement scripts
├── dashboard/                 # HTML dashboard
├── docs/                      # Architecture & measurement reports
├── evidence/                  # Measurement JSON artifacts
├── products/                  # Product stub directories
│   ├── adv_ml/
│   ├── dataset_poison/
│   ├── hf_scanner/
│   ├── llm_redteam/
│   ├── mcp_gateway/
│   ├── model_privacy/
│   └── pulsenet/
├── tests/                     # Integration & unit tests
│   ├── integration/           # Gateway health tests
│   └── test_attack_v19_detector.py
├── docker-compose.yml         # Main compose (all services)
├── docker-compose.prod.yml    # Production compose
├── docker-compose.redteam.yml # Red-team testing compose
├── Dockerfile.gateway         # Gateway container
├── Dockerfile.kali            # Kali attacker container
├── Dockerfile.wireshark       # Traffic capture container
├── gateway_server.py          # FastAPI gateway (proxy to products)
├── spec_service.py            # Spec service stub
├── Makefile                   # Build/test/lint targets
├── pyproject.toml             # Project metadata & tool config
├── requirements.txt           # Minimal runtime dependencies
└── README.md                  # Project overview
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `API_KEY environment variable is required` | Set `API_KEY` env var (≥32 chars) before running gateway or compose |
| `MLSEC_API_KEY env var not set` | Product servers need `MLSEC_API_KEY` — set it or use Docker Compose which passes `API_KEY` |
| pytest import errors | Run `pip install -e ".[dev]"` to install the package in editable mode |
| Docker build fails | Ensure Docker daemon is running; check individual `products/*/Dockerfile` |
| ruff finds no files | ruff config in `pyproject.toml` is scoped to specific files; use `ruff check .` to override |

---

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`) runs on push/PR and includes:

- Compose config validation
- Lint (ruff)
- Tests (pytest with coverage)
- Security scans (bandit, pip-audit)

---

*Last updated: 2026-08-17*
