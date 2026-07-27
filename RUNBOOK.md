# Runbook

## Engineering Update - 2026-07-27

Repository: unified-ml-security-platform
Purpose: Unified ML security platform/spec surface

## Build

- Install: make install
- Lint: make lint
- Format: make format
- Test: make test
- Package build: make build
- Security scan: make security
- Full local gate: make verify

## Dashboard

3D dashboard is still pending; build system added first per push priority.

## Dependencies And Data

Remaining work: add static dashboard and broader full-suite verification.

## Validation Snapshot

Validated: Ruff passed for attacks/attack_v19_detector.py; Makefile dry-run passed.

## Operating Limits

- Re-check Linux and GitHub Actions after pushing to main.
- Treat local dashboard scores as evidence indicators, not certifications.
- Do not cite production readiness until clean CI, dependency audit, license status, and runtime smoke tests are current.