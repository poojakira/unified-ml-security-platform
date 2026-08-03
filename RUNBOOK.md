# Runbook

Step-by-step instructions for working with this repository locally.

## Prerequisites

- Python 3.12+
- Docker (optional, for compose validation)
- PowerShell (commands below are written for Windows)

## Setup

1. Create a virtual environment:
   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install --upgrade pip
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

2. Verify Python files compile without syntax errors:
   ```powershell
   .\.venv\Scripts\python.exe -m py_compile spec_service.py
   .\.venv\Scripts\python.exe -m py_compile gateway_server.py
   .\.venv\Scripts\python.exe -m py_compile attacks\attack_v19_detector.py
   ```

## Running Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

## Makefile Targets

If you have `make` available:

| Command | What it does |
|---------|--------------|
| `make install` | Install dependencies |
| `make lint` | Run ruff linter |
| `make format` | Auto-format with ruff |
| `make test` | Run pytest |
| `make build` | Build package |
| `make security` | Run security checks (bandit, pip-audit) |
| `make verify` | Run all of the above in sequence |

## Docker Compose (Validation Only)

These commands check that the compose files are syntactically valid. They do **not** start services.

```powershell
docker compose -f docker-compose.yml config
docker compose -f docker-compose.redteam.yml config
```

Note: The compose files define services (API gateway, dashboard, prometheus, grafana) but have not been verified as a working deployment. Treat them as a design reference.

## Cross-Repo Portfolio Check

Requires sibling checkouts of the 7 implementation repos in the parent directory.

```powershell
$repoRoot = (Resolve-Path ..).Path
.\.venv\Scripts\python.exe benchmarks\portfolio_measure.py --root $repoRoot
```

This runs local regression checks across the repos and produces a measurement report.

## Known Limitations

- CI workflows exist but need re-verification on Linux / GitHub Actions after changes
- Dashboard is incomplete (static HTML only)
- Docker services have not been tested as a running stack
- Local results are evidence indicators, not certifications of correctness
