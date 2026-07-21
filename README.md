# ML Security Architecture Spec

This repository specifies a target integration architecture for the ML-security portfolio. It is not a production platform and does not contain the seven product implementations.

Use the linked implementation repositories for runnable software:

| Slot | Implementation repository | Role |
|------|---------------------------|------|
| 1 | `poojakira/hf-model-provenance-scanner` | Model supply-chain scanning and pickle-risk analysis |
| 2 | `poojakira/mcp-security-gateway-monitor` | MCP tool-call monitoring and exfiltration detection |
| 3 | `poojakira/adversarial-ml-lab` | Adversarial robustness evaluation |
| 4 | `poojakira/llm-redteam-framework` | LLM prompt-risk experiments |
| 5 | `poojakira/dataset-poisoning-detector` | Dataset poisoning and anomaly checks |
| 6 | `poojakira/model-privacy-attacks` | Privacy-attack evaluation |
| 7 | `poojakira/PulseNet-RUL-Forecasting` | Secure predictive-maintenance reference project |

See `ARCHITECTURE.md`, `STATUS.md`, `INTEGRATION_MAP.md`, `docs/PORTFOLIO_HONESTY_REPORT.md`, `docs/INDUSTRY_RESEARCH_BENCHMARK.md`, and `docs/MEASUREMENT_REPORT_2026-07-21.md` for the intended design boundaries, verified results, graphs, glossary, industry comparison bar, claim policy, focused measurements, and skeptical limitations.

## Attacker and User Runbook

See [ATTACKER_AND_USER_RUNBOOK.md](ATTACKER_AND_USER_RUNBOOK.md) for normal user/operator commands and safe [TEST-ONLY] adversarial regression commands.
