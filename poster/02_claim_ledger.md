# Claim Ledger - Poster 07

> Verified code snapshot: `d54336b5f5f058a4d756bf2c7a023ad8510bbd6f`; successful CI/CD run `37173681100`, 2026-10-04.

| # | Claim | Classification | Evidence |
|---|---|---|---|
| 1 | 82 core Python tests pass | VERIFIED_AT_SNAPSHOT | Cited Python 3.12 unit-test snapshot. |
| 2 | 95.96% statement coverage | VERIFIED_AT_SNAPSHOT | Same unit job. |
| 3 | Authenticated gateway routes four production HTTP service slots | VERIFIED_AT_SNAPSHOT | Gateway/README/production Compose contract at the cited snapshot. |
| 4 | Local Compose product containers are contract stubs | VERIFIED_AT_SNAPSHOT | `docker-compose.yml`, README, CI stub-health jobs. |
| 5 | Production Compose requires externally supplied product images | VERIFIED_AT_SNAPSHOT | `docker-compose.prod.yml`; local stubs are not built there. |
| 6 | Local stub health proves product business logic | UNSUPPORTED | Stubs validate integration contracts only. |
| 7 | Production reliability/load SLO | UNSUPPORTED | No deployment/load evidence establishes it. |

The old "three real backends" statement has been removed because it blurred local stubs with production product slots.


## Claim audit and rendered-source boundary, October 13, 2026 UTC

The reviewed printed claims, source and test commit anchors, CI dates and benchmark limitations are in `verified_claims.json`. The PDF is generated from that manifest and the PNG is rasterized from the same page by `render_poster.py`. Source inventory, dated CI and separate reported experiments must not be combined into one result. Earlier artifact versions remain in Git history; these corrections do not assert production readiness.

Offline poster rendering: `python -m pip install reportlab==4.4.9 PyMuPDF==1.26.6`, then `python poster/render_poster.py`. The font is bundled with the pinned ReportLab package; no browser or network fetch is used during rendering.
