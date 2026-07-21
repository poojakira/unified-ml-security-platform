# Attacker and User Runbook

This file gives two safe execution paths: normal architecture-spec validation and adversarial portfolio-regression validation. Attacker commands are `[TEST-ONLY]`; they run local checks across owned repository checkouts only.

## User Run

Install Python dependencies when needed:

```powershell
py -3.12 -m pip install -r requirements.txt
```

Compile local Python entrypoints:

```powershell
py -3.12 -m py_compile spec_service.py gateway_server.py
```

Validate Compose configuration without starting containers:

```powershell
docker compose -f docker-compose.yml config
```

## Attacker Run [TEST-ONLY]

Run the focused cross-repo portfolio measurement suite from the shared clone root:

```powershell
py -3.12 benchmarks\portfolio_measure.py --root C:\tmp\mlsec-dual-audit-20260721
```

Validate the red-team Compose file syntax without starting services:

```powershell
docker compose -f docker-compose.redteam.yml config
```

## Pass Condition

All selected checks exit `0`; the generated measurement report must show `9` checks run, `9` passed, and `0` failed.

## Honest Limit

These commands prove local architecture and regression checks only. This repository remains an architecture/specification and measurement hub, not a finished unified commercial platform.
