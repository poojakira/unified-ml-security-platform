# Claim Ledger - Poster 07

> Verified code snapshot: `01e58ba257764e47e230a3eecd5a821bb85e7985`; successful CI/CD run `36783840279`, 2026-09-30.

| # | Claim | Classification | Evidence |
|---|---|---|---|
| 1 | 67 core Python unit tests pass | VERIFIED_AT_SNAPSHOT | Current-main Python 3.12 unit job. |
| 2 | 56.89% statement coverage | VERIFIED_AT_SNAPSHOT | Same unit job. |
| 3 | Authenticated gateway routes four production HTTP service slots | VERIFIED_AT_SNAPSHOT | Current gateway/README/production Compose contract. |
| 4 | Local Compose product containers are contract stubs | VERIFIED_AT_SNAPSHOT | `docker-compose.yml`, README, CI stub-health jobs. |
| 5 | Production Compose requires externally supplied product images | VERIFIED_AT_SNAPSHOT | `docker-compose.prod.yml`; local stubs are not built there. |
| 6 | Local stub health proves product business logic | UNSUPPORTED | Stubs validate integration contracts only. |
| 7 | Production reliability/load SLO | UNSUPPORTED | No deployment/load evidence establishes it. |

The old "three real backends" statement has been removed because it blurred local stubs with production product slots.
