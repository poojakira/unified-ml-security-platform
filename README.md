# unified-ml-security-platform

Docker Compose wrapper and integration spec for the ML security portfolio repos. Defines how the individual tools would compose into a unified service if deployed together.

## What This Is

- A `docker-compose.yml` that wires up the portfolio repos behind a shared gateway
- A gateway server (`gateway_server.py`) that routes requests to individual services
- Architecture docs describing the intended integration points
- An ATT&CK v19 detection module (`attacks/`) shared across services

## What This Is Not

This is not a running platform. The individual repos (linked below) are the actual implementations. This repo defines how they'd talk to each other in a multi-service deployment.

## Structure

```
docker-compose.yml       - Service definitions for local multi-container testing
gateway_server.py        - FastAPI gateway routing to product services
products/                - Dockerfile + stub server for each tool
attacks/                 - ATT&CK v19 detection catalog and detector
ARCHITECTURE.md          - Target integration design
INTEGRATION_MAP.md       - Service contract requirements
```

## Implementation Repos

- [mcp-agent-security-gateway](https://github.com/poojakira/mcp-agent-security-gateway)
- [hf-model-provenance-scanner](https://github.com/poojakira/hf-model-provenance-scanner)
- [aws-agent-identity-guard](https://github.com/poojakira/aws-agent-identity-guard)
- [adversarial-ml-lab](https://github.com/poojakira/adversarial-ml-lab)
- [llm-redteam-framework](https://github.com/poojakira/llm-redteam-framework)
- [dataset-poisoning-detector](https://github.com/poojakira/dataset-poisoning-detector)
- [model-privacy-attacks](https://github.com/poojakira/model-privacy-attacks)

## Usage

```bash
docker-compose up --build
# Services start on internal network, gateway exposes port 8000
```

## Status

Learning project. The compose file builds and services start, but end-to-end integration testing is incomplete.
