# Security Audit — unified-ml-security-platform

**Audit date:** 2026-09-29  
**Scope:** gateway HTTP boundary, service-to-service authentication, proxying, Docker production topology, resource amplification, error handling, and CI.

## Findings captured before this remediation pass

| ID | Severity | Finding | Status |
|---|---|---|---|
| UMP-001 | High | Gateway endpoints have no request-rate limiter; `/correlate` amplifies one external request into multiple internal service calls. | Open |
| UMP-002 | Medium | `/correlate` fans out sequentially without a gateway-wide concurrency budget, increasing resource occupancy under load. | Open |
| UMP-003 | Medium | No browser-origin policy is configured for a deployment intended to accept requests only from an owned domain. | Open |
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
