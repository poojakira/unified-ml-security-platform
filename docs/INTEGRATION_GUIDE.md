# Integration Guide — Adding a Runtime Security Service

A service should be added to the synchronous gateway only when it has a real,
versioned, independently tested HTTP runtime contract. Batch tools must remain
batch tools until such a contract exists.

## Admission requirements

Before adding a gateway route, the owning repository must provide:

- a versioned OCI image built from a non-root runtime image
- independent CI with tests, lint/type checks, dependency/security scanning
- an unauthenticated liveness endpoint
- a readiness endpoint when startup state/dependencies matter
- authenticated business endpoints
- bounded request sizes and bounded expensive work
- explicit fail-open/fail-closed semantics
- release provenance/SBOM where supported
- a documented stable internal port and route contract

## Registering a service

Add it to both dictionaries in `gateway_server.py`:

```python
SERVICE_URLS = {
    "your_service": "http://your-service:8010",
}

SERVICE_KEY_ENV = {
    "your_service": "YOUR_SERVICE_API_KEY",
}
```

The service credential must be at least 32 characters and is validated at
gateway startup.

## Production Compose

Production uses an externally released image. Do not rebuild product
functionality from platform stubs.

```yaml
your-service:
  image: ${YOUR_SERVICE_IMAGE:?digest-pinned released image required}
  environment:
    API_KEY: ${YOUR_SERVICE_API_KEY:?service key required}
  healthcheck:
    test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8010/ready', timeout=3).read()"]
  networks: [mlsec-internal]
  restart: unless-stopped
```

Prefer `image@sha256:digest` references for release deployments.

## Gateway security contract

The gateway:

- accepts only `GET`, `POST`, `PUT`, `DELETE`, and `PATCH`
- requires the external `X-API-Key`
- drops caller-controlled `Authorization`, `Cookie`, and `X-API-Key`
- forwards only an explicit safe header set
- injects the configured service credential
- rejects bodies over the gateway maximum
- maps upstream timeout to 504 and connection/protocol failure to 502

Do not design a backend that depends on caller credentials being forwarded.

## Health vs readiness

Use `/health` for process liveness. Use `/ready` when the service requires
state such as a baseline, model, policy bundle, database migration, or external
dependency before receiving traffic.

A service that is live but unsafe to serve traffic must return non-200 from
readiness.

## Local contract stub

If a local stub is useful, it may live under `products/<service>/`, but:

- it must be labelled as a contract stub
- non-health business routes must return 501
- CI must call it “stub/contract health,” not product functionality
- the production Compose file must never use it

## Required tests

At minimum add tests for:

- missing/invalid external gateway key -> 401
- valid route is recognized
- unknown route -> 404
- caller auth/cookie headers are not forwarded
- service-specific gateway identity is injected
- oversized request -> 413 before upstream call
- upstream timeout -> 504
- other upstream failure -> 502 without stack trace
- startup fails when the service credential is missing/too short

For stateful backends, add readiness tests that prove traffic is rejected until
safe initialization completes.

## Batch tools

Do not add a fake gateway route merely so a batch project appears “integrated.”
Prefer a CI/release job that invokes its real CLI/container and publishes
machine-readable evidence. Convert it to a runtime service only when a durable
service API is actually implemented and tested.
