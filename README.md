# Unified ML Security Platform

API gateway that aggregates all ML security portfolio tools behind a single authenticated endpoint. Calls scan functions directly from installed packages — missing packages degrade gracefully and are reported via `/status`.

## Prerequisites

- Python 3.10+
- At minimum, `aws-agent-identity-guard` installed

## Install

```powershell
git clone https://github.com/poojakira/unified-ml-security-platform.git
cd unified-ml-security-platform
py -m pip install -r requirements.txt
py -m pip install aws-agent-identity-guard
```

## Run

```powershell
$env:GATEWAY_API_KEY = "your-32-char-api-key-here-abcdef"
py -m uvicorn gateway_server:app --port 9000
```

Note: The environment variable is `API_KEY` internally. Set it as:

```powershell
$env:API_KEY = "your-32-char-api-key-here-abcdef"
py -m uvicorn gateway_server:app --port 9000
```

## Test

```powershell
curl -X POST http://localhost:9000/scan/iam `
  -H "X-API-Key: your-32-char-api-key-here-abcdef" `
  -H "Content-Type: application/json" `
  -d '{"policy_document": {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "bedrock:*", "Resource": "*"}]}}'
```

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Health check |
| GET | `/status` | Yes | Available scan services report |
| POST | `/scan/iam` | Yes | Scan IAM policy for AI-agent risks |
| POST | `/scan/model` | Yes | Scan model directory for supply-chain risks |

## Available Scanners

| Service | Package | Status |
|---------|---------|--------|
| IAM Scanner | `aws-agent-identity-guard` | Required |
| HF Scanner | `hf-model-provenance-scanner` | Optional |
| Adversarial ML | `adversarial-ml-lab` | Optional |

Services not installed return HTTP 503 with install instructions.
