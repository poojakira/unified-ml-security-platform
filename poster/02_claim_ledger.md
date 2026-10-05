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
