# Product Validation

## Product boundary
Integration/control-plane layer for the AI-security product family. Individual scanners and evaluators remain separate evidence-producing engines.

## Real-world validation ladder
1. Product health and security-contract tests.
2. Cross-service authentication and finding-schema compatibility.
3. Pin each child product to a full 40-character Git commit or OCI sha256 digest. Production startup fails closed when any routed child lacks immutable release provenance.
4. End-to-end request path across at least two real child services, with correlation completeness reported explicitly and fail-closed behavior when a required child is unavailable.
5. External pilot with a real ML/agent workflow before any production-readiness claim.

## Evidence rules
Stub health endpoints are not product validation. A platform release must record which child revisions were exercised.


## Production provenance contract

The gateway status surface records the exact configured release identifier for every routed child product. Development may report an unconfigured release, but `PLATFORM_ENV=production` requires immutable release IDs before the gateway starts. This makes platform evidence traceable without pretending the local contract stubs are the real products.

## Correlation decision contract

`GATEWAY_CORRELATION_MODE=fail_closed` is the default. A correlation response is marked `complete=true` only when every routed security service returned successfully. In fail-closed mode, any unavailable/error child produces HTTP 503 while preserving the partial evidence and per-service status for operators. `best_effort` is an explicit analyst mode; it still returns `complete=false` and must not be used as proof that every security control evaluated the input.

`UPSTREAM_PRODUCTS.json` records intended upstream source revisions. Runtime release IDs are separately supplied through immutable Git SHA or OCI digest environment variables; the registry file alone is not deployment proof.
