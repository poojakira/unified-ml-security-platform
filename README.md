# Unified ML Security Platform

> ## ⚠️ ARCHITECTURE SPECIFICATION — This is not a running platform
>
> This repository defines a **deployment topology and integration contract** for 7 ML security repos.
> It contains **no functional services**. The service stubs under `products/` only expose `/health` endpoints.
> The Docker Compose files describe an intended topology that **has never been validated as a running stack**.
>
> For actual working tools, see:
> - [aws-agent-identity-guard](https://github.com/poojakira/aws-agent-identity-guard) — AWS IAM identity guardrails for AI agents
> - [hf-model-provenance-scanner](https://github.com/poojakira/hf-model-provenance-scanner) — Hugging Face model supply-chain scanner (12/12 incident reproductions passing)

---

## What This Repo Actually Contains

| Item | Status |
|------|--------|
| Architecture diagram | ✅ Reference only |
| ATT&CK v19 detection contract | ✅ Rule-based spec (not a trained model) |
| Docker Compose topology | ⚠️ Syntax-valid but never run end-to-end |
| Service stubs (`products/`, `spec_service.py`, `gateway_server.py`) | ⚠️ `/health` endpoints only — no business logic |
| Seed ATT&CK detector (`attacks/attack_v19_detector.py`) | ⚠️ Pattern-matching rules, not a production detector |
| Dashboard (`dashboard/index.html`) | ⚠️ Static HTML placeholder |

---

## Architecture Diagram (Reference)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        UNIFIED ML SECURITY PLATFORM                         │
│                          (unified-ml-security-platform)                     │
│                           [Architecture spec — not a running stack]         │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   API Gateway │  │  Dashboard   │  │  Prometheus  │  │   Grafana    │   │
│  │   (FastAPI)   │  │  (Streamlit) │  │   Metrics    │  │  Dashboards  │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                 │                 │                 │           │
│         └─────────────────┼─────────────────┼─────────────────┘           │
│                           ▼                 ▼                             │
│                  ┌──────────────────────────────────┐                    │
│                  │     ATT&CK Mapping Engine        │                    │
│                  │   (attack-v19-core v19.1.0)      │                    │
│                  │  TA0005=Stealth, TA0112=DefImp   │                    │
│                  └──────────────┬───────────────────┘                    │
│                                 │                                       │
└─────────────────────────────────┼───────────────────────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ MODEL SUPPLY    │    │ LLM / GATEWAY   │    │ ADVERSARIAL /   │
│ CHAIN SECURITY  │    │ DEFENSE         │    │ PRIVACY         │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ hf-model-       │    │ mcp-security-   │    │ adversarial-ml- │
│ provenance-     │    │ gateway-monitor │    │ lab             │
│ scanner         │    │                 │    │ model-privacy-  │
│                 │    │                 │    │ attacks         │
│ T1195.001       │    │ T1684, T1687    │    │ T1685, T1689    │
│ T1683/001       │    │ T1685           │    │ T1682           │
│ T1027/018       │    │ T1689           │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    SHARED INFRASTRUCTURE                                │
│  attack-v19-core (v19.1.0)  │  attack-detection-engine (v1.0.0)       │
│  222 techniques, 475 subs   │  5 detectors (log/traffic/behavior/      │
│  TA0005=Stealth             │  event/code)                             │
│  TA0112=DefImp              │  20+ patterns, 80% coverage target       │
│  V19_REVOCATION_MAP (17)    │                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Linked Repositories (Actual Implementations)

| # | Repository | What it does | Status |
|---|-----------|--------------|--------|
| 1 | [hf-model-provenance-scanner](https://github.com/poojakira/hf-model-provenance-scanner) | Scans HF models for supply-chain risks | ✅ Strong prototype (12/12 fixtures) |
| 2 | [aws-agent-identity-guard](https://github.com/poojakira/aws-agent-identity-guard) | AWS IAM guardrails for AI agents | ✅ Working tool |
| 3 | [mcp-security-gateway-monitor](https://github.com/poojakira/mcp-security-gateway-monitor) | MCP tool-call security monitor | ✅ Substantial prototype (~51% detection) |
| 4 | [llm-redteam-framework](https://github.com/poojakira/llm-redteam-framework) | Prompt injection detection | Baseline (F1=0.70 OOD) |
| 5 | [adversarial-ml-lab](https://github.com/poojakira/adversarial-ml-lab) | FGSM/PGD/C&W attack library | Educational |
| 6 | [dataset-poisoning-detector](https://github.com/poojakira/dataset-poisoning-detector) | Anomaly screening for training data | Research baseline (AUC ~0.53) |
| 7 | [model-privacy-attacks](https://github.com/poojakira/model-privacy-attacks) | Membership inference & extraction | Educational |
| 8 | [PulseNet-RUL-Forecasting](https://github.com/poojakira/PulseNet-RUL-Forecasting) | ICS predictive maintenance | Reference implementation |

---

## What the Service Stubs Do

The files `spec_service.py`, `gateway_server.py`, and the `products/` directory contain **minimal stubs** that:

- Return `{"status": "ok"}` on `/health`
- Do **not** implement any scanning, detection, monitoring, or analysis logic
- Exist solely to define the intended API surface for future integration

These are wiring placeholders, not implementations.

---

## Docker Compose (Topology Spec Only)

The `docker-compose.yml` describes the intended multi-service topology. It has **never been validated as a running stack**.

```powershell
# Syntax check only — confirms valid YAML, does NOT prove the services run
docker compose -f docker-compose.yml config
```

---

## ATT&CK v19 Mapping

Shared conventions across all linked repos:
- **TA0005** = Stealth (renamed from Defense Evasion in v19)
- **TA0112** = Defense Impairment (new in v19)
- 17 revoked techniques remapped via `V19_REVOCATION_MAP`
- Detection contract defined in `docs/ATTACK_V19_DETECTION_CONTRACT.md`

---

## Documentation

- `ARCHITECTURE.md` — high-level design
- `INTEGRATION_MAP.md` — how repos connect
- `STATUS.md` — current state of each component
- `docs/PORTFOLIO_HONESTY_REPORT.md` — honest assessment of what works and what doesn't
- `docs/ATTACK_V19_DETECTION_CONTRACT.md` — which techniques each repo owns

---

## License

MIT
