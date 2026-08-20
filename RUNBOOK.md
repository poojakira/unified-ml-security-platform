# RUNBOOK — unified-ml-security-platform

## Prerequisites

- Docker 20.10+
- Docker Compose v2.x
- 8 GB RAM minimum (16 GB recommended)
- Ports 8000-8010 available

## Bring Up Services

```bash
docker-compose up -d --build
```

Services started: API gateway, MIA service, poisoning detector, model inversion, dashboard.

## Health Checks

```bash
docker-compose ps
# All containers should show "Up (healthy)"

# Individual service check:
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
```

If a service is unhealthy, check its logs (below) and restart:
```bash
docker-compose restart <service-name>
```

## Logs

```bash
# All services:
docker-compose logs -f

# Single service:
docker-compose logs -f mia-service

# Last 100 lines:
docker-compose logs --tail=100 poisoning-detector
```

## Run a Job

```bash
curl -X POST http://localhost:8000/api/v1/scan \
  -H "Content-Type: application/json" \
  -d '{"model_path": "/models/target.pkl", "dataset_path": "/data/train.csv"}'
```

Poll status: `GET http://localhost:8000/api/v1/scan/{job_id}`

## Teardown

```bash
# Stop and remove containers, networks:
docker-compose down

# Also remove volumes (DESTRUCTIVE — deletes stored results):
docker-compose down -v
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Port conflict | Edit `docker-compose.yml` port mappings or stop conflicting process |
| Container restart loop | Check `docker-compose logs <svc>` for startup errors |
| OOM kills | Increase Docker memory limit in Docker Desktop settings |
| Stale images after code change | `docker-compose up -d --build --force-recreate` |
| Network unreachable between services | `docker-compose down && docker-compose up -d` to reset network |
