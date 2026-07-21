# Portfolio Measurement Report

Generated UTC: 2026-07-21T22:47:03+00:00

## Scope

This report measures focused security and correctness checks against the local checked-out branches. It does not measure market superiority, production scale, customer telemetry, or independent commercial benchmarks.

## Summary

- Checks run: 9
- Passed: 9
- Failed: 0
- Raw JSON evidence: `evidence/portfolio_measurement_2026-07-21.json`

## Results

| Repo/check | Status | Duration ms | Pytest summary | Purpose |
|---|---:|---:|---|---|
| repo1-mcp-security-gateway-monitor | PASS | 3448 | 20 passed in 0.11s | Prompt-injection normalization and BCC header bypass regression tests. |
| repo2-hf-model-provenance-scanner | PASS | 4564 | 15 passed in 0.82s | Pickle magic-byte and scanner regression tests for renamed payload coverage. |
| repo3-PulseNet-RUL-Forecasting | PASS | 5610 | 7 passed in 0.70s | JWT secret hardening and audit-log integrity regression tests. |
| repo4-dataset-poisoning-detector | PASS | 13607 | 7 passed in 9.73s | False-positive budget and slow-drift poisoning detection regression tests. |
| repo5-llm-redteam-framework | PASS | 6619 | 4 passed in 3.11s | LLM classifier false-positive budget enforcement tests. |
| repo6-model-privacy-attacks | PASS | 10479 | 9 passed in 6.98s | Privacy attack implementation and probability-fidelity regression tests. |
| repo7-adversarial-ml-lab | PASS | 11399 | 30 passed in 5.62s | Benchmark signing and verification integrity tests. |
| repo8-unified-ml-security-platform | PASS | 168 | n/a | Architecture-spec service compile validation. |
| repo8-unified-ml-security-platform-compose | PASS | 382 | n/a | Self-contained docker-compose syntax/config validation. |

## Commands Executed

### repo1-mcp-security-gateway-monitor

Working directory: `../repo1-mcp`

```powershell
py -3.12 -m pytest tests/test_normalization_pipeline.py tests/test_bcc_normalization.py -q
```

Exit code: `0`

Stdout tail:

```text
....................                                                     [100%]
20 passed in 0.11s
```

### repo2-hf-model-provenance-scanner

Working directory: `../repo2-hf`

```powershell
py -3.12 -m pytest tests/test_pickle_scanner.py -q
```

Exit code: `0`

Stdout tail:

```text
...............                                                          [100%]
15 passed in 0.82s
```

Stderr tail:

```text
C:\Users\pooja\AppData\Local\Programs\Python\Python312\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
```

### repo3-PulseNet-RUL-Forecasting

Working directory: `../repo3-pulsenet`

```powershell
py -3.12 -m pytest tests/test_auth_secret.py tests/test_extra_coverage.py::TestAuditLogger -q
```

Exit code: `0`

Stdout tail:

```text
.......                                                                  [100%]
7 passed in 0.70s
```

### repo4-dataset-poisoning-detector

Working directory: `../repo4-poison`

```powershell
py -3.12 -m pytest tests/test_drift.py tests/test_fp_budget.py -q
```

Exit code: `0`

Stdout tail:

```text
.......                                                                  [100%]
7 passed in 9.73s
```

Stderr tail:

```text
C:\Users\pooja\AppData\Local\Programs\Python\Python312\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
```

### repo5-llm-redteam-framework

Working directory: `../repo5-redteam`

```powershell
py -3.12 -m pytest tests/test_fp_budget.py
```

Exit code: `0`

Stdout tail:

```text
....                                                                     [100%]
4 passed in 3.11s
```

### repo6-model-privacy-attacks

Working directory: `../repo6-privacy`

```powershell
py -3.12 -m pytest tests/test_privacy_attacks.py -q
```

Exit code: `0`

Stdout tail:

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.3.4, pluggy-1.6.0
rootdir: C:\tmp\mlsec-dual-audit-20260721\repo6-privacy
configfile: pyproject.toml
plugins: anyio-4.12.1, Faker-37.12.0, langsmith-0.9.3, asyncio-0.25.3, cov-6.0.0, mock-3.15.1, zarr-3.1.5
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None
collected 9 items

tests\test_privacy_attacks.py .........                                  [100%]

============================== 9 passed in 6.98s ==============================
```

Stderr tail:

```text
C:\Users\pooja\AppData\Local\Programs\Python\Python312\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
```

### repo7-adversarial-ml-lab

Working directory: `../repo7-adv`

```powershell
py -3.12 -m pytest tests/test_ci_signing.py tests/test_benchmark_verify.py -q
```

Exit code: `0`

Stdout tail:

```text
..............................                                           [100%]
30 passed in 5.62s
```

### repo8-unified-ml-security-platform

Working directory: `../repo8-platform`

```powershell
py -3.12 -m py_compile spec_service.py gateway_server.py
```

Exit code: `0`

### repo8-unified-ml-security-platform-compose

Working directory: `../repo8-platform`

```powershell
docker compose -f docker-compose.yml config
```

Exit code: `0`

Stdout tail:

```text
  pulsenet:
    build:
      context: C:\tmp\mlsec-dual-audit-20260721\repo8-platform
      dockerfile: products/pulsenet/Dockerfile
    deploy:
      resources:
        limits:
          cpus: 1
          memory: "1073741824"
    environment:
      API_KEY: ""
      PULSENET_JWT_SECRET: ""
    networks:
      mlsec-internal: null
    restart: unless-stopped
networks:
  mlsec-internal:
    name: repo8-platform_mlsec-internal
    driver: bridge
    internal: true
```

## Honest Interpretation

Passing these checks means the local branches satisfy focused regression gates selected for this remediation pass. It does not prove the products are unhackable or better than mature commercial platforms.

A legitimate commercial comparison still requires independent benchmark corpora, latency and false-positive measurements on production-like benign traffic, SIEM/telemetry verification, supply-chain evidence, and repeated runs across clean environments.
