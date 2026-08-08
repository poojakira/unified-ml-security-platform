# Unified ML Security Platform

API gateway aggregating all ML security tools behind a single authenticated endpoint.

Instead of running separate tools independently, this gateway exposes a unified REST API that calls scan functions directly from installed portfolio packages. Missing packages degrade gracefully — the `/status` endpoint reports what's available.

## Install

```bash
# Clone and install the gateway
git clone https://github.com/poojakira/unified-ml-security-platform.git
cd unified-ml-security-platform
pip install -e ".[dev]"

# Install the scan backends
pip install aws-agent-identity-guard hf-model-provenance-scanner
```

## Configuration

Set the required environment variable:

```bash
export API_KEY="your-api-key-at-least-32-characters-long"
```

## Run

```bash
uvicorn gateway_server:app --host 0.0.0.0 --port 8000
```

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Health check for load balancers |
| GET | `/status` | Yes | Reports which scan services are installed and available |
| POST | `/scan/iam` | Yes | Scan IAM policy document for AI-agent risks |
| POST | `/scan/model` | Yes | Scan local model path for supply-chain risks |

### POST /scan/iam

Scans an IAM policy document using [aws-agent-identity-guard](https://github.com/poojakira/aws-agent-identity-guard) (22 rules targeting Bedrock, SageMaker, Lambda, ECS, Step Functions).

```json
{
  "policy_document": {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": "bedrock:*",
        "Resource": "*"
      }
    ]
  }
}
```

### POST /scan/model

Scans a local model directory using [hf-model-provenance-scanner](https://github.com/poojakira/hf-model-provenance-scanner) (taint engine, symbolic resolution, temporal scanning).

```json
{
  "path": "/path/to/model/directory"
}
```

### GET /status

Returns availability of each backend:

```json
{
  "status": "operational",
  "services": {
    "iam_scanner": {"available": true, "package": "aws-agent-identity-guard"},
    "hf_scanner": {"available": true, "package": "hf-model-provenance-scanner"},
    "adv_ml": {"available": false, "package": "adversarial-ml-lab"}
  },
  "installed": 2,
  "total": 3
}
```

## Authentication

All endpoints except `/health` require the `X-API-Key` header matching the `API_KEY` environment variable.

## Requirements

Requires individual tools installed:

```bash
pip install aws-agent-identity-guard hf-model-provenance-scanner
```

Optional (for adversarial robustness benchmarks):
```bash
pip install adversarial-ml-lab
```

## Product Services

Individual product wrappers are available under `products/` for microservice deployments:

- `products/hf_scanner/server.py` — HF model provenance scanning
- `products/adv_ml/server.py` — Adversarial robustness benchmarking

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -q
```

## License

MIT
