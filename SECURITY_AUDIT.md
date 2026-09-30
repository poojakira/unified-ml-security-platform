# Security Audit — unified-ml-security-platform

**Audit date:** 2026-09-29  
**Scope:** gateway HTTP boundary, service-to-service authentication, proxying, Docker production topology, resource amplification, error handling, and CI.

## Findings captured before this remediation pass

| ID | Severity | Finding | Status |
|---|---|---|---|
| UMP-001 | High | Gateway requests are now bounded by a per-peer/API-key rate limiter before authenticated work, including `/correlate`. | Fixed |
| UMP-002 | Medium | `/correlate` now acquires a configurable gateway-wide semaphore before fan-out, bounding simultaneous correlation workloads across callers. | Fixed |
| UMP-003 | Medium | CORS is not used as an authentication boundary: the gateway uses an explicit `X-API-Key` and has no cookie-authenticated browser session. No repository evidence establishes a required owned-domain browser client, so adding a restrictive CORS policy would be speculative. | N/A / False positive |
| UMP-004 | Info | Upstream targets are a fixed internal allowlist and external Authorization/Cookie headers are not forwarded. | Verified |

## Existing controls verified

- Separate 32+ character gateway and per-service credentials.
- Bounded proxy body size.
- Fixed internal service targets.
- Header allowlist.
- Shared httpx client and upstream timeouts.
- Generic upstream failure responses with request IDs.
- Internal Docker network; only gateway is published in production compose.
- Non-root gateway image.
- Secret-hygiene CI.

## Verification plan

Add low-overhead gateway throttling, concurrency control, optional owned-origin policy, then run integration/production workflows.
