# unified-ml-security-platform

Architecture specification hub for the ML security portfolio. Defines integration contracts, shared detection schemas, and Docker Compose validation across the 7 implementation repositories. Not a running product.

See the implementation repos for actual tools:
[mcp-agent-security-gateway](https://github.com/poojakira/mcp-agent-security-gateway) ·
[hf-model-provenance-scanner](https://github.com/poojakira/hf-model-provenance-scanner) ·
[aws-agent-identity-guard](https://github.com/poojakira/aws-agent-identity-guard) ·
[adversarial-ml-lab](https://github.com/poojakira/adversarial-ml-lab) ·
[llm-redteam-framework](https://github.com/poojakira/llm-redteam-framework) ·
[dataset-poisoning-detector](https://github.com/poojakira/dataset-poisoning-detector) ·
[model-privacy-attacks](https://github.com/poojakira/model-privacy-attacks)

## Contents

- `ARCHITECTURE.md` — target integration architecture
- `docs/ATTACK_V19_DETECTION_CONTRACT.md` — shared finding schema all tools conform to
- `INTEGRATION_MAP.md` — how tools compose
- `docker-compose.yml` — inter-service communication validation
- `attacks/attack_v19_detector.py` — seed detector implementing the contract baseline
