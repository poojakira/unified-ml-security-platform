# Runbook — Unified ML Security Platform

Step-by-step guide to run the gateway server and test the security platform.

---

## Prerequisites

- Python 3.12+ (`py --version` on Windows, `python3 --version` on Linux)
- pip (bundled with Python)
- Git
- Docker (optional, for compose validation)

---

## Step 1: Clone and Install Requirements

**Windows (PowerShell):**
```powershell
git clone https://github.com/poojakira/unified-ml-security-platform.git
cd unified-ml-security-platform
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**Linux/macOS:**
```bash
git clone https://github.com/poojakira/unified-ml-security-platform.git
cd unified-ml-security-platform
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Verify compilation:
```powershell
.\.venv\Scripts\python.exe -m py_compile gateway_server.py
.\.venv\Scripts\python.exe -m py_compile attacks\attack_v19_detector.py
```

---

## Step 2: Install aws-agent-identity-guard

The gateway uses `aws-agent-identity-guard` for IAM policy scanning.

**Windows (PowerShell):**
```powershell
.\.venv\Scripts\python.exe -m pip install aws-agent-identity-guard
```

**Linux/macOS:**
```bash
pip install aws-agent-identity-guard
```

Verify:
```powershell
.\.venv\Scripts\python.exe -c "import aws_agent_identity_guard; print('OK')"
```

---

## Step 3: Set GATEWAY_API_KEY Environment Variable

The gateway requires an API key for authentication.

**Windows (PowerShell):**
```powershell
$env:GATEWAY_API_KEY = "change-me-to-a-32-char-min-secret-key"
```

**Linux/macOS:**
```bash
export GATEWAY_API_KEY="change-me-to-a-32-char-min-secret-key"
```

> **Note:** For local development, any non-empty string works. For production, use a strong random key (32+ characters).

---

## Step 4: Start the Gateway Server

**Windows (PowerShell):**
```powershell
.\.venv\Scripts\python.exe -m uvicorn gateway_server:app --port 8080
```

**Linux/macOS:**
```bash
uvicorn gateway_server:app --port 8080
```

Expected output:
```
INFO:     Started server process [XXXX]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8080 (Press CTRL+C to quit)
```

---

## Step 5: Test with curl (Scan IAM Policy)

**Windows (PowerShell):**
```powershell
# Submit an IAM policy for scanning
curl -X POST http://localhost:8080/api/scan `
  -H "Content-Type: application/json" `
  -H "X-API-Key: change-me-to-a-32-char-min-secret-key" `
  -d '{\"policy_document\": {\"Version\": \"2012-10-17\", \"Statement\": [{\"Effect\": \"Allow\", \"Action\": \"bedrock:*\", \"Resource\": \"*\"}]}}'
```

**Linux/macOS:**
```bash
curl -X POST http://localhost:8080/api/scan \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me-to-a-32-char-min-secret-key" \
  -d '{"policy_document": {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "bedrock:*", "Resource": "*"}]}}'
```

Expected response — list of findings/violations:
```json
{
  "findings": [
    {
      "rule_id": "AIG-001",
      "severity": "HIGH",
      "message": "Overly permissive Bedrock wildcard action"
    }
  ]
}
```

---

## Step 6: Verify /status Endpoint

**Windows (PowerShell):**
```powershell
curl http://localhost:8080/status
```

**Linux/macOS:**
```bash
curl http://localhost:8080/status
```

Expected response:
```json
{
  "status": "healthy",
  "version": "...",
  "uptime_seconds": ...
}
```

---

## Running Tests

**Windows (PowerShell):**
```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

**Linux/macOS:**
```bash
pytest tests -q
```

---

## Makefile Targets (if `make` is available)

| Command | What it does |
|---------|--------------|
| `make install` | Install dependencies |
| `make lint` | Run ruff linter |
| `make format` | Auto-format with ruff |
| `make test` | Run pytest |
| `make build` | Build package |
| `make security` | Run security checks (bandit, pip-audit) |
| `make verify` | Run all of the above in sequence |

---

## Docker Compose (Validation Only)

These check that compose files parse correctly. They do **not** start services:

```powershell
docker compose -f docker-compose.yml config
docker compose -f docker-compose.redteam.yml config
```

> **Note:** The compose files define services but have not been verified as a working deployment. Treat them as a design reference.

---

## Cross-Repo Portfolio Check

Requires sibling checkouts of the implementation repos:

```powershell
$repoRoot = (Resolve-Path ..).Path
.\.venv\Scripts\python.exe benchmarks\portfolio_measure.py --root $repoRoot
```

---

## Troubleshooting

### Port Already in Use

```
ERROR: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8080)
```

**Fix:**
```powershell
# Find what's using port 8080
netstat -ano | findstr :8080

# Kill the process or use a different port
.\.venv\Scripts\python.exe -m uvicorn gateway_server:app --port 8081
```

---

### Authentication Errors (401 / 403)

**Fix:**
1. Ensure `GATEWAY_API_KEY` is set:
   ```powershell
   echo $env:GATEWAY_API_KEY
   ```
2. Ensure your curl includes the correct header:
   ```powershell
   -H "X-API-Key: change-me-to-a-32-char-min-secret-key"
   ```
3. Key in the header must match `GATEWAY_API_KEY` exactly.

---

### ModuleNotFoundError on Startup

```
ModuleNotFoundError: No module named 'fastapi'
```

**Fix:**
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

### aws-agent-identity-guard Not Found

```
ModuleNotFoundError: No module named 'aws_agent_identity_guard'
```

**Fix:**
```powershell
.\.venv\Scripts\python.exe -m pip install aws-agent-identity-guard
```

---

### Tests Fail with Import Errors

Ensure you're running pytest from the venv:
```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Not:
```powershell
pytest tests -q  # might use system Python
```

---

## Files Reference

| File | Purpose |
|------|---------|
| `gateway_server.py` | FastAPI gateway — IAM policy scanning endpoint |
| `requirements.txt` | Python dependencies |
| `attacks/attack_v19_detector.py` | ATT&CK v19 technique detection |
| `attacks/attack_catalog.py` | Attack technique catalog |
| `attacks/attack_client.py` | Attack simulation client |
| `tests/` | Pytest test suite |
| `products/` | Product integrations (HF scanner, MCP, etc.) |
| `benchmarks/portfolio_measure.py` | Cross-repo measurement script |
| `docker-compose.yml` | Service definitions (design reference) |
| `dashboard/index.html` | Static dashboard page |

---

## Known Limitations

- This is an architecture spec — service stubs have limited logic
- Docker compose services have not been tested as a running stack
- CI workflows need re-verification on Linux after local changes
- Dashboard is static HTML only (not connected to live data)
- Local results are development indicators, not production certifications
