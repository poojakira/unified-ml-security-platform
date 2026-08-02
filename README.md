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

Use the supporting documents when you need a specific answer:

- `ARCHITECTURE.md`: the proposed system design.
- `STATUS.md`: what is implemented here and what is only planned.
- `INTEGRATION_MAP.md`: how the implementation repositories fit together.
- `docs/PORTFOLIO_HONESTY_REPORT.md`: claim boundaries and known limitations.
- `docs/MEASUREMENT_REPORT_2026-07-21.md`: recorded measurements and how they were collected.
- `docs/INDUSTRY_RESEARCH_BENCHMARK.md`: research context, not proof of product performance.

## ATT&CK v19 Detection Contract

This repo now includes a shared MITRE ATT&CK v19 detection contract for Enterprise, Mobile, and ICS scope in `docs/ATTACK_V19_DETECTION_CONTRACT.md`, plus a dependency-free seed detector in `attacks/attack_v19_detector.py`.

This is a rule/contract baseline for the seven products. It must not be described as a fully trained ATT&CK model until official MITRE CTI ingestion and validation against all applicable techniques/sub-techniques are implemented.

## Real-World Boundary

This repository can be real-world useful as an architecture, measurement, and integration-spec hub. It is **not** a real-time unified commercial platform by itself. Real-time protection exists only in implementation repos that are deployed inline, especially `poojakira/mcp-security-gateway-monitor` for MCP tool-call inspection. Claims such as "unhackable", "100 layers block every attacker", or "beats all mature commercial platforms" are not legitimate without production traffic, latency, false-positive, incident-response, and independent benchmark evidence.

## Attacker and User Runbook

See [ATTACKER_AND_USER_RUNBOOK.md](ATTACKER_AND_USER_RUNBOOK.md) for normal user/operator commands and safe [TEST-ONLY] adversarial regression commands.

## Operational Runbook

Verified architecture-hub path uses [ATTACKER_AND_USER_RUNBOOK.md](ATTACKER_AND_USER_RUNBOOK.md). Minimal validation:

```powershell
py -3.12 -m pip install -r requirements.txt
py -3.12 -m py_compile spec_service.py gateway_server.py attacks\attack_v19_detector.py
py -3.12 -m pytest tests -q
```

Scope note: this repository is an architecture/spec hub. It now includes an ATT&CK v19 detection contract and seed detector, not a fully trained production model.

# trigger

<!-- engineering-update-2026-07-27 -->
## Engineering Update - 2026-07-27

Scope: Unified ML security platform/spec surface.

Current hardening pass:
- Build system: Makefile targets added or verified for install, lint, format, test, build, security, and verify.
- Dashboard: 3D dashboard is still pending; build system added first per push priority.
- ATT&CK mapping: repos that map detections now use the shared v19 mapping builder where applicable.
- Validation: Validated: Ruff passed for attacks/attack_v19_detector.py; Makefile dry-run passed.

<!-- /engineering-update-2026-07-27 -->
