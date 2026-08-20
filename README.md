# unified-ml-security-platform

Docker Compose integration workspace that orchestrates 7 ML security microservices behind a FastAPI gateway (8 services total) on an internal bridge network. Provides compose validation, health checks, resource limits, and a shared ATT&CK v19 detection module.

## Architecture

```
                         ┌─────────────┐
                         │   Gateway   │ :8000 / :8443
                         └──────┬──────┘
        ┌────────┬────────┬─────┼─────┬────────┬────────┬─────────┐
        ▼        ▼        ▼     ▼     ▼        ▼        ▼         ▼
   hf-scanner  mcp-gw  adv-ml  llm-  dataset-  model-  pulsenet  attacks/
                               redteam poison   privacy           (shared)
        └────────┴────────┴─────┴─────┴────────┴────────┴─────────┘
                         mlsec-internal (bridge, no egress)
```

## Services (docker-compose.prod.yml)

| Service         | CPU | Memory | Health Check |
|-----------------|-----|--------|--------------|
| gateway         | 2   | 2 GB   | curl /health |
| hf-scanner      | 1   | 1 GB   | —            |
| mcp-gateway     | 1   | 1 GB   | —            |
| adv-ml          | 2   | 4 GB   | —            |
| llm-redteam     | 1   | 2 GB   | —            |
| dataset-poison  | 1   | 1 GB   | —            |
| model-privacy   | 1   | 1 GB   | —            |
| pulsenet        | 1   | 1 GB   | —            |

## Quick Start

```bash
# Build and start all services
docker-compose -f docker-compose.prod.yml up --build

# Gateway exposes :8000 (HTTP) and :8443 (HTTPS)
curl http://localhost:8000/health
```

## Development

```bash
make install     # install deps + dev tools (ruff, bandit, pip-audit)
make test        # pytest tests/
make lint        # ruff check
make security    # bandit + pip-audit
make verify      # lint + test + build + security
```

## Key Components

- `gateway_server.py` — FastAPI reverse proxy routing to internal services
- `attacks/` — Shared ATT&CK v19 detection catalog (attack_catalog.py, attack_v19_detector.py)
- `products/` — Dockerfile + stub server per service
- `docker-compose.prod.yml` — Production-grade compose (no debug containers)

## Network Security

All services communicate on `mlsec-internal`, a bridge network with `internal: true` (no external access). Only the gateway exposes ports. API key auth via `$API_KEY` env var.

## Related Repos

This workspace composes services from: [mcp-agent-security-gateway](https://github.com/poojakira/mcp-agent-security-gateway), [hf-model-provenance-scanner](https://github.com/poojakira/hf-model-provenance-scanner), [aws-agent-identity-guard](https://github.com/poojakira/aws-agent-identity-guard), [adversarial-ml-lab](https://github.com/poojakira/adversarial-ml-lab), [llm-redteam-framework](https://github.com/poojakira/llm-redteam-framework), [dataset-poisoning-detector](https://github.com/poojakira/dataset-poisoning-detector), [model-privacy-attacks](https://github.com/poojakira/model-privacy-attacks).

## License

Apache License 2.0
