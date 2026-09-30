# Security review, 30 September 2026

Reviewed baseline: `cd8ea430d201a9226cf6047574b01b6a18207531`. Source review and focused regression verification; this is not proof that all vulnerabilities are absent.

## Fixes and reviewed controls

Gateway rate budget is keyed by peer rather than attacker-selected invalid credentials and has a hard 4096-identity bound. Gateway JSON and proxy bodies are bounded before parsing. Direct product services now have 1 MiB body caps and 60 requests/minute per-peer limits with bounded state. UTF-8 byte comparisons handle invalid non-ASCII keys. Packaging includes products.common. Setup examples include the required model-privacy credential. Runtime floors exclude audited vulnerable Starlette/AnyIO versions.

## Verification

117 gateway/product tests passed; the required coverage gate also passed at 76.77% before the final overflow regression. Tests ran in an isolated Python 3.12 environment. FastAPI TestClient required execution outside the default sandbox; a minimal unchanged app reproduced the sandbox deadlock. Final installed-environment pip-audit reported no known vulnerabilities. This does not cover every optional dependency, every container image, or arbitrary older environments allowed by broad dependency bounds.

## Secret history review

Eight historical matches were CI/test keys and documentation examples. No tracked environment or private-key paths found in fetched history. Gitleaks classifications are pattern matches, not provider validity checks. No provider key was tested or revoked, and fetched Git refs do not include every cached/forked copy. `.env` and local credential patterns remain ignored; example files must contain placeholders only.

## Deployment and remaining limits

The gateway key intentionally authorizes all configured service proxy routes. Separate service credentials authenticate service-to-service requests but are not per-user authorization. Put backends on a private network; these architecture wrappers are not substitutes for all upstream products. Correlation returns partial results when a backend is unavailable. All rate windows are per process; multiple workers need a shared ingress policy. Body caps do not replace ingress read-timeouts, response caps, or resource limits.
