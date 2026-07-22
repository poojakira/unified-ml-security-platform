# Attacker and User Runbook

This file gives two safe execution paths: normal architecture-spec validation and adversarial portfolio-regression validation. Attacker commands are `[TEST-ONLY]`; they run local checks across owned repository checkouts only.

## User Run
Create an isolated PowerShell environment before running repository commands:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

Install Python dependencies when needed:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Compile local Python entrypoints:

```powershell
.\.venv\Scripts\python.exe -m py_compile spec_service.py gateway_server.py
```

Validate Compose configuration without starting containers:

```powershell
docker compose -f docker-compose.yml config
```

## Attacker Run [TEST-ONLY]

Run the focused cross-repo portfolio measurement suite from the shared clone root:

```powershell
$repoRoot = (Resolve-Path ..).Path
.\.venv\Scripts\python.exe benchmarks\portfolio_measure.py --root $repoRoot
```

Validate the red-team Compose file syntax without starting services:

```powershell
docker compose -f docker-compose.redteam.yml config
```


Validate MCP missed-attack coverage in the implementation checkout:

```powershell
$repoRoot = (Resolve-Path ..).Path
Push-Location (Join-Path $repoRoot "repo1-mcp")
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m pytest tests/test_advanced_correlation.py tests/test_pii_detector.py tests/test_prompt_injection.py tests/test_shadow_server.py tests/test_exfiltration.py -q
Pop-Location
```
## Pass Condition

All selected checks exit `0`; the generated measurement report must show `9` checks run, `9` passed, and `0` failed.

## Honest Limit

These commands prove local architecture and regression checks only. This repository remains an architecture/specification and measurement hub, not a finished unified commercial platform.



