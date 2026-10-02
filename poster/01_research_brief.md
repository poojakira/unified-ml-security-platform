# Research Brief - Poster 07

> Evidence status: Refreshed against verified code snapshot `26aace469f65e46cbbf38525aa0a36f6eca6d53b` and successful CI/CD run `36944325113` on 2026-09-30.

## Repository

`github.com/poojakira/unified-ml-security-platform` - public, default branch `main`.

## Academic Project Title

**A Unified Control Plane for Machine-Learning Security Services**

### Subtitle

An Authenticated Gateway for Independently Released ML Security Products

## One-Sentence Contribution

A real authenticated FastAPI control plane with **four production HTTP service slots**, a local contract-test topology built from stubs, and a production Compose contract that requires externally released product images instead of pretending the stubs are product implementations.

## Method

1. Authenticate external callers at the gateway.
2. Strip caller-controlled sensitive headers and inject per-service credentials.
3. Route four synchronous service prefixes over an internal-only network.
4. Use local health-contract stubs to test topology without misrepresenting product logic.
5. Require explicit external product images in production Compose.
6. Validate unit, security, integration, image-build, and deployment-contract behavior in CI.

## Verified Evidence at Poster Snapshot

The cited Python 3.12 unit-test snapshot reports:

- **76 tests passed**.
- **95.78% statement coverage**.
- Separate local contract-stub health jobs for MCP, LLM red-team, dataset-poison, and model-privacy completed successfully.
- Integration topology tests completed successfully.
- Security scan, dependency audit, production Compose validation, and gateway image build/push job completed successfully.

## Critical Claim Correction

The previous poster said the gateway fronted "three real backends." That is not an accurate description of the current repository. The correct boundary is:

- local Compose uses **contract stubs**;
- production Compose defines **four externally supplied real product image slots**;
- stub health checks prove routing/topology contracts only, not downstream product functionality.

## Limitations

- Product business logic is owned by external repositories/images.
- No production deployment, uptime, or load SLO is established.
- Multi-replica shared rate limiting/state distribution requires deployment-specific infrastructure.
- Batch tools such as HF provenance scanning and adversarial robustness are intentionally not forced behind synchronous HTTP routes.

## Reproducibility

```bash
git clone https://github.com/poojakira/unified-ml-security-platform.git
cd unified-ml-security-platform
git checkout 26aace469f65e46cbbf38525aa0a36f6eca6d53b
python -m pip install -e ".[dev]"
pytest tests/ -q --cov=. --cov-report=term
docker compose config
docker compose -f docker-compose.prod.yml config
```

Expected core Python evidence: **76 passed**, **95.78% coverage**.
