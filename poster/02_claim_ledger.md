# Claim Ledger — Poster 07 (07-unified-ml-security-platform)

Apache-2.0 • Python 3.12 • HEAD cbcdd43 • verified 2026-09-26. Classification: VERIFIED_CURRENT / VERIFIED_HISTORICAL / PARTIAL / UNVERIFIED / UNSUPPORTED.

| # | Claim | Classification | Evidence |
|---|---|---|---|
| 1 | 59 test functions across suite | VERIFIED_CURRENT | Counted def test_ in tests/ (HEAD cbcdd43). |
| 2 | One authenticated FastAPI gateway fronts 3 real backends | VERIFIED_CURRENT | ARCHITECTURE.md runtime boundary: X-API-Key, header allowlist, body-size limit, timeout/error map; backends internal-only. |
| 3 | Only gateway publishes a host port | VERIFIED_CURRENT | ARCHITECTURE.md: production Docker network internal-only. |
| 4 | Async orchestration / backend accuracy / production SLO | UNSUPPORTED (disclaimed) | ARCHITECTURE.md: synchronous control plane; accuracy is per-backend; no SLO claimed. |

## Policy applied
- Only VERIFIED_CURRENT figures appear as prominent current results.
- Historical/projected values are labeled (dashed box / explicit note).
- Unsupported production/accuracy claims are omitted or shown in the red "NOT ESTABLISHED" box.
