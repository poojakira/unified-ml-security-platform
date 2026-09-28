# Verified Metrics — Poster 07

> Evidence status: This is a dated repository snapshot at the commit identified below. `VERIFIED_AT_SNAPSHOT` means verified for that commit and environment; it does not assert the same result on the latest `main`. Compare newer claims with the repository evidence before reuse.

Apache-2.0 • Python 3.12 • HEAD cbcdd43 • verified 2026-09-26. Verified for this poster on Windows / CPython 3.12.10.

## Headline cards
- 59 — TEST FUNCTIONS
- 3 — REAL BACKENDS
Notes: 59 test_ functions across the platform test suite. Three integrated HTTP products behind one gateway.

## Verified surface
| Item | Value |
|---|---|
| Public host ports | 1 |
| Auth mechanism | API key |
| Compose files | 2 |

## Chart values
| Series | Value |
|---|---|
| Caller auth | 100 |
| Header allowlist | 100 |
| Body-size limit | 100 |
| Error mapping | 100 |
Note: Controls implemented at the gateway entry. Backend enforcement depth is per-tool, not shown here.

## Historical / provenance
ARCHITECTURE.md documents a synchronous control plane + separate batch/admission jobs. Production Docker network is internal-only; gateway alone exposed.

## Not established by this repository
Backend detector accuracy. Distributed orchestration. Production reliability, uptime, or throughput SLOs.
