# Unified ML Security Platform (Architecture Spec)

[![Demo Dashboard (static)](https://img.shields.io/badge/Demo_Dashboard-Static-lightgrey)](https://poojakira.github.io/unified-ml-security-platform/)

This repository is an architecture specification and integration hub. It defines how 7 separate ML security repositories fit together. It is **not** a running platform — the actual implementations live in the linked repos below.

## What This Repo Contains

- An architecture diagram showing how the 7 repos connect
- A shared MITRE ATT&CK v19 detection contract (`docs/ATTACK_V19_DETECTION_CONTRACT.md`)
- A seed rule-based ATT&CK detector (`attacks/attack_v19_detector.py`) — not a trained model
- Docker Compose files describing the intended deployment topology (not verified in production)
- A benchmark script for running local checks across sibling repo checkouts
- Stub product directories under `products/` (wiring, not implementations)

## ⚠️ Red-Team Files (docker-compose.redteam.yml, Dockerfile.kali, Dockerfile.exfil)

These files exist for **local development testing only** — they simulate attacker infrastructure to validate the defensive layers. In a real deployment:

- Attack tooling MUST be deployed in a **separate AWS account** (isolated from production)
- Red-team infrastructure MUST NOT share VPC, IAM roles, or deployment pipelines with defensive services
- This co-location is acceptable for a local Docker Compose development environment but violates AWS Well-Architected (SEC-5) and NIST 800-53 (CA-8) for production deployments

If deploying to AWS, separate these into an isolated red-team account with cross-account trust only for authorized pen-test roles.

## Linked Repositories (Actual Implementations)

| # | Repository | What it does |
|---|-----------|--------------|
| 1 | `poojakira/hf-model-provenance-scanner` | Scans Hugging Face models for supply-chain risks (pickle exploits, unsigned weights, typosquatting) |
| 2 | `poojakira/mcp-security-gateway-monitor` | Monitors MCP tool calls for prompt injection and data exfiltration attempts |
| 3 | `poojakira/adversarial-ml-lab` | Runs adversarial attacks (FGSM, PGD, C&W) and evaluates defenses |
| 4 | `poojakira/llm-redteam-framework` | Generates and detects adversarial prompts (jailbreaks, refusal bypasses) |
| 5 | `poojakira/dataset-poisoning-detector` | Detects label-flip and backdoor poisoning in datasets |
| 6 | `poojakira/model-privacy-attacks` | Evaluates membership inference and model extraction attacks |
| 7 | `poojakira/PulseNet-RUL-Forecasting` | Predictive maintenance with ICS ATT&CK v19 technique mappings |

## How to Use This Repo

This repo is useful for:
- Understanding how the 7 repos relate to each other
- Running cross-repo regression checks locally
- Referencing the ATT&CK v19 detection contract

It is **not** useful as a standalone security tool. You need the individual repos above for that.

### Local Validation

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m py_compile spec_service.py gateway_server.py attacks\attack_v19_detector.py
.\.venv\Scripts\python.exe -m pytest tests -q
```

### Cross-Repo Measurement (requires sibling checkouts)

```powershell
.\.venv\Scripts\python.exe benchmarks\portfolio_measure.py --root (Resolve-Path ..).Path
```

### Docker Compose (syntax check only — not verified as a running stack)

```powershell
docker compose -f docker-compose.yml config
```

## ATT&CK v19 Mapping

The repos share a common ATT&CK v19 mapping convention:
- TA0005 = Stealth (renamed from Defense Evasion in v19)
- TA0112 = Defense Impairment (new in v19)
- 17 revoked techniques are remapped via a shared revocation map

The detection contract in `docs/ATTACK_V19_DETECTION_CONTRACT.md` defines which techniques each repo is responsible for. This is a rule-based contract, not a trained ML detection model.

## Current State

- Build: Makefile targets exist for `install`, `lint`, `format`, `test`, `build`, `security`, `verify`
- Tests: `attacks/attack_v19_detector.py` passes ruff lint; pytest runs locally
- Dashboard: Planned but not complete (`dashboard/index.html` exists as a static file)
- CI: GitHub Actions workflows exist but should be re-verified after pushing to main
- Docker: Compose files define services but have not been validated as a running stack

## Documentation

- `ARCHITECTURE.md` — high-level design
- `INTEGRATION_MAP.md` — how repos connect
- `STATUS.md` — current state of each component
- `docs/PORTFOLIO_HONESTY_REPORT.md` — honest assessment of what works and what doesn't
- `docs/MEASUREMENT_REPORT_2026-07-21.md` — local measurement results
- `docs/INDUSTRY_RESEARCH_BENCHMARK.md` — comparison context (not independent validation)
- `ATTACKER_AND_USER_RUNBOOK.md` — step-by-step commands for validation and regression testing

## License

MIT
