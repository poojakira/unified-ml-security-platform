# Research Brief — Poster 07

## Repository
`github.com/poojakira/unified-ml-security-platform` (public, default branch `main`, primary language Python). Apache-2.0 • Python 3.12 • HEAD 7ac348c • verified 2026-09-26

## Academic Project Title
**A Unified Control Plane for Machine-Learning Security Services**

### Subtitle
An Authenticated Gateway Fronting Heterogeneous ML Security Products

## One-Sentence Contribution
A synchronous authenticated control plane that fronts three real ML security services (MCP gateway, LLM red-team, dataset-poison) with consistent auth, header allowlisting, body-size limits, and uniform error mapping on an internal-only Docker network.

## Problem Statement
Each ML security tool ships its own HTTP service, auth model, and error semantics. Wiring them into a product means every caller re-implements auth, header handling, body limits, and timeouts — inconsistently. A single gateway normalizes the entry boundary for the three real backend services.

## Threat Model
Chain: EXTERNAL CALLER -> API-KEY BOUNDARY -> HEADER ALLOWLIST -> TIMEOUT / ERROR MAP -> BACKEND SERVICE.
Adversary capability: sends crafted requests to the public port; Assumptions: only gateway is exposed; backends internal-only; Out of scope: backend detector accuracy; per-tool enforcement depth; Residual risk: gateway is single entry; auth key hygiene.

## Research / Engineering Question
> Can heterogeneous ML security services be fronted by one authenticated control plane with consistent auth, limits, and error handling?

## Objective
Determine whether one FastAPI gateway can provide consistent auth, allowlisting, limits, and error mapping across three ML security backends.

## Engineering Sub-Objectives
O1 — X-API-Key caller auth
O2 — Header allowlist + body-size limit
O3 — Timeout + uniform error mapping
O4 — Internal-only backend network

## Methodology
1 Receive (HTTP) -> 2 Auth (X-API-Key) -> 3 Allowlist (headers) -> 4 Limit (body size) -> 5 Route (backend) -> 6·7 Map (timeout/error)

## Current Verified Evidence + Claim Ledger
- **VERIFIED_CURRENT** — 59 test functions across suite — Counted def test_ in tests/ (HEAD 7ac348c).
- **VERIFIED_CURRENT** — One authenticated FastAPI gateway fronts 3 real backends — ARCHITECTURE.md runtime boundary: X-API-Key, header allowlist, body-size limit, timeout/error map; backends internal-only.
- **VERIFIED_CURRENT** — Only gateway publishes a host port — ARCHITECTURE.md: production Docker network internal-only.
- **UNSUPPORTED (disclaimed)** — Async orchestration / backend accuracy / production SLO — ARCHITECTURE.md: synchronous control plane; accuracy is per-backend; no SLO claimed.

## Important Negative / Honest Results
See RESULTS panel: Controls implemented at the gateway entry. Backend enforcement depth is per-tool, not shown here.

## Limitations
1. Gateway normalizes entry, not backend accuracy.
2. Synchronous control plane; not an async orchestrator.
3. Single public entry point (blast-radius consideration).
4. Local tests ≠ production reliability.
5. Per-tool enforcement depth varies (documented).

## Future Work
• Async / queued orchestration mode.
• Per-backend rate limiting.
• Distributed multi-replica state strategy.
• End-to-end integration benchmark.
• mTLS between gateway and backends.

## Reproducibility
```
docker compose up -d
pytest tests/
```
Evidence: ARCHITECTURE.md, INTEGRATION_MAP.md, tests/

## References
[1] OWASP API Security Top 10 · [2] FastAPI docs · [3] OWASP Top 10 for LLM Apps · [4] MITRE ATLAS · [5] NIST AI RMF 1.0 · [6] Docker network security
