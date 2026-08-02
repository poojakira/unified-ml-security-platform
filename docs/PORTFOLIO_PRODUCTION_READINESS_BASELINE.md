# Portfolio Production-Readiness Baseline

**Owner:** Pooja Kiran (`poojakira`)
**Status:** Baseline and acceptance checklist; **not a production certification**
**Scope:** Curated AI/ML-security repositories reviewed in August 2026

## What "production-ready" means here

A repository is production-ready only when a specific deployment has all of the following evidence:

1. A supported installation and rollback procedure for the target operating system.
2. Authentication, authorization, secret rotation, and least-privilege identity controls appropriate to the deployment.
3. Health checks, structured logs, metrics, alert routing, and an identified operational owner.
4. A reproducible security and dependency scan with reviewable artifacts.
5. A representative benchmark or evaluation with source data/model revision, environment, command, raw result, and limitations.
6. A threat model and incident response procedure for the data and tools actually deployed.
7. Deployment-specific load, failure, recovery, and access-control tests.

Passing a unit test suite, generating an SBOM, or having a Dockerfile is useful evidence but does not independently meet this definition.

## Current portfolio classification

| Repository | Current role | Readiness classification | Highest remaining gap |
|---|---|---|---|
| `mcp-security-gateway-monitor` | Agent tool-call security control plane | Prototype / pre-production candidate | Inline deployment, real workload evaluation, operational ownership |
| `hf-model-provenance-scanner` | Model supply-chain scanner | Prototype / pre-production candidate | Real artifact corpus and downloaded-model performance evidence |
| `llm-redteam-framework` | Offline LLM evaluation research tool | Research | External benchmark datasets and deployment interface |
| `dataset-poisoning-detector` | Dataset anomaly research service | Research | Representative datasets and calibrated false-positive policy |
| `model-privacy-attacks` | Privacy attack evaluation library | Research | Reproducible target-model and dataset benchmark artifacts |
| `adversarial-ml-lab` | Robustness evaluation lab | Research | Real model weights, GPU benchmark, and result artifacts |
| `PulseNet-RUL-Forecasting` | Secure predictive-maintenance reference service | Deployment evidence incomplete | Real provenance values, operating owner, and deployment validation |
| `attack-detection-engine` | ATT&CK telemetry detector library | Prototype / pre-production candidate | Product API contract, benchmark corpus, and operational interface |
| `attack-v19-core` | ATT&CK data library | Library, not a service | Data-refresh provenance and release policy |
| `aws-agent-identity-guard` | Static policy analyzer | Prototype / pre-production candidate | Real policy corpus and integration ownership |
| `mlsec-benchmark-suite` | Evidence/benchmark infrastructure | Research infrastructure | Product adapters, public datasets, and populated result artifacts |
| `unified-ml-security-platform` | Architecture and integration specification | Specification, not a service | Real integrated runtime and common control plane |
| `poojakira` | Portfolio evidence index | Documentation/evidence repository | Downstream evidence freshness only |
| `-AEROSEC` | Placeholder | Not assessable | Product scope, code, tests, and operating model |
| `production-ml-platform` | ML platform prototype | Not assessable from current remote state | Accessible remote, supported runbook, deployment evidence |

## High-priority production candidates

The portfolio should not be deployed as one platform today. The most credible path is to select one narrowly scoped service at a time.

### 1. MCP Security Gateway

**Good next candidate:** an internal, authenticated agent-tool proxy with loopback or private-network deployment.

Before deployment, require:

- A real inline client integration that fails according to an agreed fail-open or fail-closed policy.
- Per-tool authorization and scoped service credentials.
- A stable event store instead of in-memory dashboard statistics.
- Alert destination, ownership, incident severity, and retention policy.
- A representative evaluation corpus covering allowed traffic, BCC exfiltration, SSRF, prompt injection, and egress bypass attempts.
- Load and recovery tests on the intended deployment hardware.

### 2. HF Model Provenance Scanner

**Good next candidate:** a CI or model-admission scan that blocks high-confidence unsafe artifacts and reports lower-confidence findings.

Before deployment, require:

- Immutable repository/model revisions in every scan result.
- A public or internal fixture corpus with licensing and expected findings.
- Performance results on actual downloaded artifacts, not only metadata fixtures.
- Clear severity policy: block, warn, review, or allow.
- Signed release and dependency provenance for the scanner itself.

## Safe hardening already implemented

The following controls were implemented and validated during this portfolio pass:

- A repository-owned security gate for `attack-detection-engine`:
  - Bandit SAST
  - pip-audit dependency audit
  - CycloneDX SBOM generation
  - checked-in security policy evaluator
  - reviewable workflow artifacts
- Dependency remediations for audited Scapy, lxml, and setuptools findings.
- Current GitHub Actions success for the repositories updated during the pass.
- A Windows-runnable ATT&CK v18-to-v19 migration guide with verified core and consumer commands.
- Corrected cross-repository migration guide links.
- Explicit README evidence boundaries for fixture-based HF latency and false-positive results.
- A self-contained unified gateway health test rather than a dependency on an arbitrary localhost service.

## Evidence requirements for public benchmark claims

A public number may be used in a README, resume, or demo only when all required evidence is committed or linked from a stable artifact:

| Evidence item | Required |
|---|---:|
| Exact command | Yes |
| Source commit | Yes |
| Dependency lock/version | Yes |
| Dataset/model revision and license | Yes |
| OS, Python, hardware, and accelerator details | Yes |
| Raw JSON/CSV result | Yes |
| Aggregated report | Yes |
| Known limitations and failure cases | Yes |

If any item is missing, use descriptive wording instead of a numerical performance claim.

## Deployment acceptance checklist

Use this checklist for one selected service and environment. Do not mark a repository production-ready before every applicable item has evidence.

### Security

- [ ] Threat model reviewed for the actual data, model, tools, and identities.
- [ ] Authentication and authorization tested.
- [ ] Secrets are stored outside source code and rotation is documented.
- [ ] Dependency scan and SBOM are generated for the release candidate.
- [ ] Security findings have owner, severity, due date, and disposition.

### Reliability and operations

- [ ] Health and readiness endpoints are tested in the target environment.
- [ ] Structured logs and metrics have a retained destination.
- [ ] Alert owner and on-call escalation path are defined.
- [ ] Backup, recovery, and rollback are tested.
- [ ] Load test reflects expected traffic and resource limits.

### Evidence and model/data governance

- [ ] Inputs, datasets, model artifacts, and configuration are versioned.
- [ ] Benchmark output is reproducible from committed commands.
- [ ] Privacy, retention, and data-classification decisions are documented.
- [ ] Residual risks and known bypasses are communicated to users.

### Release approval

- [ ] A named technical owner accepts the release.
- [ ] A named security owner accepts residual risk.
- [ ] Environment-specific deployment configuration is reviewed.
- [ ] Post-deployment verification is recorded.

## Explicit non-goals

This baseline does not:

- Claim that every repository is production-ready.
- Replace a cloud security review, penetration test, or legal/privacy assessment.
- Authorize cloud deployment, billing, production credentials, data ingestion, or public exposure.
- Convert research metrics into external benchmark claims.

## Next decision

Select one candidate service, deployment target, data classification, authentication method, secrets manager, and operational owner. Then use the acceptance checklist above to create a deployment-specific plan.
