# Runbook: unified-ml-security-platform

**Repository:** https://github.com/poojakira/unified-ml-security-platform  
**Description:** Integration workspace for ML security services with CI, compose validation, scans, and health checks  
**License:** Apache-2.0  
**Default Branch:** main

---

## Prerequisites

- Python 3.10+
- Docker & Docker Compose
- Git
- Make (optional)
- 4GB+ RAM for Docker services

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/poojakira/unified-ml-security-platform.git
cd unified-ml-security-platform

# Start all services with Docker Compose
docker-compose up -d

# Verify health checks
docker-compose ps

# Run validation script
python scripts/validate.py
```

---

## Detailed Setup

### 1. Environment Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy example config
cp config.example.yaml config.yaml

# Edit config.yaml with your settings:
# - Service ports
# - Database connections
# - API keys
# - Scan policies
```

Required environment variables:
- `POSTGRES_PASSWORD` - Database password
- `REDIS_PASSWORD` - Redis password
- `JWT_SECRET` - JWT signing secret
- `GITHUB_TOKEN` - For GitHub API integration

### 3. Start Services

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f

# Run health checks
curl http://localhost:8000/health
curl http://localhost:8001/health
```

---

## Service Architecture

| Service | Port | Description |
|---------|------|-------------|
| API Gateway | 8000 | Main entry point |
| Scanner Service | 8001 | ML model scanning |
| Auth Service | 8002 | Authentication/Authorization |
| Database | 5432 | PostgreSQL |
| Cache | 6379 | Redis |
| Message Queue | 5672 | RabbitMQ |

---

## Available Commands

### Using Makefile

```bash
# Show all targets
make help

# Start services
make up

# Stop services
make down

# Restart services
make restart

# Run tests
make test

# Run linting
make lint

# Security scan
make security

# Generate SBOM
make sbom

# View logs
make logs
```

### Docker Compose Direct

```bash
# Start in background
docker-compose up -d

# Start with build
docker-compose up -d --build

# Stop and remove volumes
docker-compose down -v

# Scale services
docker-compose up -d --scale scanner=3
```

---

## Testing

```bash
# Run unit tests
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -v

# Run all tests with coverage
pytest tests/ --cov=src --cov-report=html --cov-fail-under=80

# Run specific test
pytest tests/unit/test_scanner.py::test_scan_model -v
```

---

## Validation & Health Checks

```bash
# Run validation script
python scripts/validate.py

# Check all service health endpoints
for port in 8000 8001 8002; do
  echo "Service on port $port:"
  curl -s http://localhost:$port/health | jq .
done

# Verify scanner functionality
python scripts/test_scanner.py --model-path ./test-models/sample.pt
```

---

## CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/ci.yml`):

- **Compose Validation:** Validates docker-compose.yml syntax
- **Service Health:** Starts services and verifies health endpoints
- **Security Scans:** Runs Trivy, Bandit, and pip-audit
- **Integration Tests:** Runs full test suite against running services
- **SBOM Generation:** Creates Software Bill of Materials
- **SARIF Upload:** Uploads security findings to GitHub Security

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Port already in use | Check `docker-compose ps` and stop conflicting services |
| Database connection failed | Ensure PostgreSQL is healthy: `docker-compose logs postgres` |
| Redis connection refused | Check Redis service: `docker-compose logs redis` |
| Scanner service fails | Check scanner logs: `docker-compose logs scanner` |
| Out of memory | Increase Docker memory limit to 4GB+ |

### Service Debugging

```bash
# Access service shell
docker-compose exec scanner bash
docker-compose exec api bash

# View service logs
docker-compose logs -f scanner
docker-compose logs -f api

# Restart single service
docker-compose restart scanner

# Rebuild single service
docker-compose up -d --build scanner
```

### Database Issues

```bash
# Access PostgreSQL
docker-compose exec postgres psql -U postgres -d mlsec

# Run migrations
docker-compose exec api python -m alembic upgrade head

# Backup database
docker-compose exec postgres pg_dump -U postgres mlsec > backup.sql
```

---

## Repository Structure

```
unified-ml-security-platform/
├── .github/workflows/     # CI/CD pipelines
├── config/                # Configuration files
├── deploy/                # Deployment manifests
├── docs/                  # Documentation
├── scripts/               # Utility scripts
├── src/                   # Source code
│   ├── api/               # API gateway
│   ├── scanner/           # Scanning services
│   ├── auth/              # Authentication
│   └── common/            # Shared utilities
├── tests/                 # Test suite
├── .env.example
├── config.example.yaml
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── README.md
├── requirements.txt
└── pyproject.toml
```

---

## Links

- **Repository:** https://github.com/poojakira/unified-ml-security-platform
- **Documentation:** See `docs/` directory
- **API Docs:** http://localhost:8000/docs (when running)

---

## Verification Checklist

- [ ] Repository clones successfully
- [ ] Docker Compose starts all services
- [ ] All health endpoints return 200 OK
- [ ] `pytest tests/` passes
- [ ] `make test` passes
- [ ] Scanner can process a test model
- [ ] API authentication works
- [ ] Database migrations apply cleanly
- [ ] SBOM generates without errors
- [ ] Security scans complete

---

*Last updated: 2026-08-16*  
*Tested on: Ubuntu 22.04, Docker 24.0, Python 3.12*