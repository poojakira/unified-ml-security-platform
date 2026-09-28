# Claim Ledger — Poster 07 (07-unified-ml-security-platform)

> Evidence status: This is a dated repository snapshot at the commit identified below. `VERIFIED_AT_SNAPSHOT` means verified for that commit and environment; it does not assert the same result on the latest `main`. Compare newer claims with the repository evidence before reuse.

Apache-2.0 • Python 3.12 • HEAD cbcdd43 • verified 2026-09-26. Classification: VERIFIED_AT_SNAPSHOT / VERIFIED_HISTORICAL / PARTIAL / UNVERIFIED / UNSUPPORTED.

| # | Claim | Classification | Evidence |
|---|---|---|---|
| 1 | 59 test functions across suite | VERIFIED_AT_SNAPSHOT | Counted def test_ in tests/ (HEAD cbcdd43). |
| 2 | One authenticated FastAPI gateway fronts 3 real backends | VERIFIED_AT_SNAPSHOT | ARCHITECTURE.md runtime boundary: X-API-Key, header allowlist, body-size limit, timeout/error map; backends internal-only. |
| 3 | Only gateway publishes a host port | VERIFIED_AT_SNAPSHOT | ARCHITECTURE.md: production Docker network internal-only. |
| 4 | Async orchestration / backend accuracy / production SLO | UNSUPPORTED (disclaimed) | ARCHITECTURE.md: synchronous control plane; accuracy is per-backend; no SLO claimed. |

## Policy applied
- Only VERIFIED_AT_SNAPSHOT figures appear as prominent current results.
- Historical/projected values are labeled (dashed box / explicit note).
- Unsupported production/accuracy claims are omitted or shown in the red "NOT ESTABLISHED" box.
