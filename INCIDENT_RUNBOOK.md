# Incident Runbook — Unified ML Security Platform Gateway

## Overview

This runbook covers operational incidents for the API Gateway that fronts the HuggingFace Model Scanner and MCP Security Gateway services.

**Architecture:**
```
Clients → [API Gateway :8000] → [HF Scanner :8001]
                               → [MCP Gateway :8002]
```

**On-call contacts:**
- Primary: Platform Engineering (#platform-oncall in Slack)
- Escalation: Security Engineering (#security-oncall in Slack)
- Page: PagerDuty `unified-ml-platform` service

---

## Incident Severity Levels

| Level | Description | Response Time | Examples |
|-------|-------------|---------------|----------|
| SEV1 | Complete outage, security bypass | 5 min | Gateway down, auth bypass |
| SEV2 | Partial outage, degraded security | 15 min | One backend down, high error rate |
| SEV3 | Performance degradation | 1 hour | High latency, rate limiting issues |
| SEV4 | Minor issue, no user impact | Next business day | Log noise, non-critical alerts |

---

## INC-001: Gateway Completely Unresponsive

### Symptoms
- `/health` endpoint returns no response or connection refused
- All API calls timeout
- Monitoring shows 0 successful requests

### Diagnosis

```bash
# Check gateway process
docker ps | grep gateway
systemctl status unified-ml-gateway

# Check port binding
ss -tlnp | grep 8000
netstat -an | grep 8000

# Check recent logs
docker logs gateway --tail 100 --since 5m
journalctl -u unified-ml-gateway --since "5 minutes ago"

# Check resource exhaustion
docker stats gateway --no-stream
free -h
df -h
```

### Resolution

1. **Process crashed:**
   ```bash
   # Restart the gateway
   docker restart gateway
   # Or with systemd:
   systemctl restart unified-ml-gateway
   ```

2. **Port conflict:**
   ```bash
   # Find and kill conflicting process
   lsof -i :8000
   kill -9 <PID>
   # Restart gateway
   docker restart gateway
   ```

3. **Resource exhaustion:**
   ```bash
   # Check and clear disk
   docker system prune -f
   # Increase memory limit
   docker update --memory 2g gateway
   # Restart
   docker restart gateway
   ```

4. **Configuration error:**
   ```bash
   # Validate config
   python -c "from gateway.app import app; print('Config OK')"
   # Check env vars
   docker exec gateway env | grep -i gateway
   # Rollback to last known good config
   docker run -d --name gateway-rollback -e CONFIG_VERSION=<previous> ...
   ```

### Post-incident
- Check why health checks didn't trigger auto-restart
- Review resource limits and auto-scaling thresholds
- Verify alerting fired within expected timeframe

---

## INC-002: Authentication/Authorization Failures

### Symptoms
- Valid tokens receiving 401 responses
- All authenticated requests failing
- Monitoring shows auth error spike

### Diagnosis

```bash
# Test with known-good token
curl -H "Authorization: Bearer ${KNOWN_GOOD_TOKEN}" http://localhost:8000/api/v1/scanner/health

# Check JWT validation
docker exec gateway python -c "
from gateway.auth import verify_token
try:
    verify_token('${TOKEN}')
    print('Token valid')
except Exception as e:
    print(f'Token invalid: {e}')
"

# Check signing key availability
docker exec gateway python -c "
from gateway.auth import get_signing_key
print(f'Key loaded: {get_signing_key() is not None}')
"

# Check clock skew (JWT exp validation)
docker exec gateway date
date
```

### Resolution

1. **Signing key rotation issue:**
   ```bash
   # Reload signing keys
   docker exec gateway kill -HUP 1
   # Or restart with key refresh
   docker restart gateway
   ```

2. **Clock skew:**
   ```bash
   # Sync NTP
   chronyc makestep
   # Or in container
   docker exec gateway ntpdate pool.ntp.org
   ```

3. **Token issuer mismatch:**
   ```bash
   # Check expected issuer configuration
   docker exec gateway env | grep JWT_ISSUER
   # Update if needed
   docker exec gateway env JWT_ISSUER=https://correct-issuer.example.com
   docker restart gateway
   ```

4. **JWKS endpoint unreachable:**
   ```bash
   # Test JWKS endpoint
   curl -v ${JWKS_URI}
   # Check DNS resolution from container
   docker exec gateway nslookup auth.example.com
   # Fallback to cached keys
   docker exec gateway env JWT_USE_CACHED_KEYS=true
   docker restart gateway
   ```

### Post-incident
- Audit all requests during auth failure window
- Check if any unauthorized access occurred
- Review key rotation procedures

---

## INC-003: Backend Service Unavailable (503)

### Symptoms
- Gateway returns 503 for specific service routes
- `/api/v1/scanner/*` or `/api/v1/mcp/*` failing
- Gateway `/health` is fine, but service health checks fail

### Diagnosis

```bash
# Check which backend is down
curl http://localhost:8001/health  # HF Scanner
curl http://localhost:8002/health  # MCP Gateway

# Check backend containers
docker ps | grep -E "scanner|mcp"
docker logs hf-scanner --tail 50
docker logs mcp-gateway --tail 50

# Check network connectivity
docker exec gateway curl http://hf-scanner:8001/health
docker exec gateway curl http://mcp-gateway:8002/health

# Check DNS resolution within network
docker exec gateway nslookup hf-scanner
docker exec gateway nslookup mcp-gateway
```

### Resolution

1. **Backend process crashed:**
   ```bash
   # Restart the specific backend
   docker restart hf-scanner  # or mcp-gateway
   
   # Verify recovery
   sleep 5
   curl http://localhost:8001/health
   ```

2. **Backend OOM killed:**
   ```bash
   # Check OOM events
   dmesg | grep -i oom
   docker inspect hf-scanner | grep -i oom
   
   # Increase memory and restart
   docker update --memory 4g hf-scanner
   docker restart hf-scanner
   ```

3. **Network partition:**
   ```bash
   # Check Docker network
   docker network inspect platform-network
   
   # Reconnect containers
   docker network disconnect platform-network hf-scanner
   docker network connect platform-network hf-scanner
   ```

4. **Dependency failure (scanner can't reach HuggingFace):**
   ```bash
   # Check external connectivity from backend
   docker exec hf-scanner curl -s https://huggingface.co/api/models?limit=1
   
   # If HuggingFace is down, enable cached-only mode
   docker exec hf-scanner env SCANNER_OFFLINE_MODE=true
   docker restart hf-scanner
   ```

### Post-incident
- Review health check intervals (should catch faster)
- Consider adding circuit breaker if not already configured
- Update dependency health monitoring

---

## INC-004: High Latency / Performance Degradation

### Symptoms
- Response times exceed SLA (p95 > 500ms)
- Client timeouts increasing
- Throughput dropping below expected levels

### Diagnosis

```bash
# Check current latency metrics
curl http://localhost:8000/metrics | grep -i latency

# Profile gateway
docker exec gateway python -c "
import psutil
p = psutil.Process(1)
print(f'CPU: {p.cpu_percent(interval=1)}%')
print(f'Memory: {p.memory_info().rss / 1024 / 1024:.0f}MB')
print(f'Threads: {p.num_threads()}')
print(f'FDs: {p.num_fds()}')
"

# Check connection pool saturation
docker exec gateway python -c "
from gateway.proxy import get_client_pool
pool = get_client_pool()
print(f'Active connections: {pool.num_connections}')
print(f'Available: {pool.num_available}')
"

# Check backend response times
time curl http://localhost:8001/health
time curl http://localhost:8002/health

# Check system resources
docker stats --no-stream
iostat -x 1 3
```

### Resolution

1. **Connection pool exhaustion:**
   ```bash
   # Increase pool size
   docker exec gateway env HTTP_POOL_SIZE=200
   docker restart gateway
   ```

2. **Slow backend causing backpressure:**
   ```bash
   # Reduce timeout to fail fast
   docker exec gateway env BACKEND_TIMEOUT_MS=5000
   docker restart gateway
   
   # Scale backend horizontally
   docker-compose up -d --scale hf-scanner=3
   ```

3. **CPU saturation:**
   ```bash
   # Scale gateway workers
   docker exec gateway env UVICORN_WORKERS=4
   docker restart gateway
   
   # Or scale horizontally
   docker-compose up -d --scale gateway=3
   ```

4. **Memory pressure / GC pauses:**
   ```bash
   # Check Python GC stats
   docker exec gateway python -c "
   import gc
   gc.collect()
   print(f'GC counts: {gc.get_count()}')
   print(f'GC thresholds: {gc.get_threshold()}')
   "
   
   # Increase memory limit
   docker update --memory 4g gateway
   ```

### Post-incident
- Run `benchmarks/gateway_perf.py` to validate recovery
- Update capacity planning if load has grown
- Consider adding auto-scaling rules

---

## INC-005: Rate Limiting Misfiring

### Symptoms
- Legitimate users hitting 429 errors
- Rate limits not applying (abuse traffic getting through)
- Inconsistent rate limit behavior across gateway instances

### Diagnosis

```bash
# Check rate limiter state
docker exec gateway python -c "
from gateway.middleware import RateLimiter
rl = RateLimiter.get_instance()
print(f'Active buckets: {rl.bucket_count}')
print(f'Config: {rl.config}')
"

# Check Redis (if external rate limit store)
redis-cli info clients
redis-cli dbsize
redis-cli TTL "ratelimit:user:affected-user-id"

# Check rate limit headers from a test request
curl -v -H "Authorization: Bearer ${TOKEN}" http://localhost:8000/api/v1/scanner/health 2>&1 | grep -i ratelimit
```

### Resolution

1. **Limits too aggressive:**
   ```bash
   # Increase rate limits
   docker exec gateway env RATE_LIMIT_PER_MINUTE=1000
   docker restart gateway
   ```

2. **Shared state desync (multi-instance):**
   ```bash
   # Check Redis connectivity
   docker exec gateway python -c "
   import redis
   r = redis.from_url('${REDIS_URL}')
   r.ping()
   print('Redis OK')
   "
   
   # Flush rate limit keys (careful — resets all limits)
   redis-cli KEYS "ratelimit:*" | xargs redis-cli DEL
   ```

3. **Rate limiter not applying (bypass):**
   ```bash
   # Verify middleware is loaded
   docker exec gateway python -c "
   from gateway.app import app
   middlewares = [m.cls.__name__ for m in app.user_middleware]
   print(f'Middlewares: {middlewares}')
   assert 'RateLimitMiddleware' in str(middlewares)
   "
   ```

### Post-incident
- Review rate limit thresholds against actual traffic patterns
- Check for legitimate high-volume users who need higher limits
- Validate rate limiter consistency across all instances

---

## INC-006: Security Incident — Potential Bypass

### Symptoms
- Unexpected 200 responses to unauthenticated requests
- Anomalous traffic patterns to backend services
- Alert from security monitoring

### Immediate Actions (SEV1)

```bash
# 1. IMMEDIATELY: Block suspicious traffic
iptables -A INPUT -s <SUSPICIOUS_IP> -j DROP

# 2. Enable enhanced logging
docker exec gateway env LOG_LEVEL=DEBUG ACCESS_LOG_FULL=true
docker restart gateway

# 3. Capture current state for forensics
docker logs gateway > /tmp/gateway-forensics-$(date +%s).log
docker exec gateway cat /tmp/access.log > /tmp/access-forensics-$(date +%s).log

# 4. Check for unauthorized access
docker exec gateway python -c "
from gateway.auth import get_active_sessions
sessions = get_active_sessions()
for s in sessions:
    print(f'{s.user_id} - {s.created_at} - {s.last_activity}')
"
```

### Diagnosis

```bash
# Check if auth middleware is active
curl -v http://localhost:8000/api/v1/scanner/scan -X POST -d '{}' 2>&1 | grep "< HTTP"
# Should be 401

# Check for path traversal bypass
curl http://localhost:8000/api/v1/../internal/debug
curl http://localhost:8000/api/v1/scanner/../../admin

# Check for header injection
curl -H "X-Forwarded-For: 127.0.0.1" http://localhost:8000/api/v1/scanner/health

# Review recent access patterns
docker exec gateway python -c "
from gateway.audit import get_recent_requests
for req in get_recent_requests(minutes=30):
    if req.status_code == 200 and not req.authenticated:
        print(f'SUSPICIOUS: {req.method} {req.path} from {req.client_ip}')
"
```

### Resolution

1. **Rotate all credentials immediately:**
   ```bash
   # Rotate JWT signing key
   python scripts/rotate_jwt_key.py
   
   # Invalidate all active sessions
   redis-cli FLUSHDB  # If using Redis session store
   
   # Restart with new key
   docker restart gateway
   ```

2. **Deploy emergency patch if vulnerability found:**
   ```bash
   # Pull latest security patch
   docker pull ghcr.io/org/unified-ml-security-platform:latest-security
   docker stop gateway
   docker run -d --name gateway-patched ... ghcr.io/org/unified-ml-security-platform:latest-security
   ```

3. **Enable WAF rules:**
   ```bash
   # Block suspicious patterns at load balancer level
   aws wafv2 update-ip-set --name blocked-ips --addresses <IP>/32
   ```

### Post-incident (MANDATORY)
- Full security audit of gateway code
- Review all access during incident window
- Notify affected users if data exposure occurred
- File CVE if vulnerability is novel
- Conduct blameless postmortem within 48 hours

---

## INC-007: Disk Space / Log Rotation Issues

### Symptoms
- Container filesystem full
- Logs not rotating
- Write failures in application

### Diagnosis

```bash
# Check disk usage
df -h
du -sh /var/lib/docker/containers/*
docker system df

# Check log sizes
ls -lah /var/lib/docker/containers/*/json.log
docker inspect gateway --format='{{.LogPath}}'
```

### Resolution

```bash
# Truncate container logs (immediate relief)
truncate -s 0 $(docker inspect gateway --format='{{.LogPath}}')

# Configure log rotation
docker update --log-opt max-size=100m --log-opt max-file=5 gateway

# Clean up old images/containers
docker system prune -af --volumes

# Long-term: Add log driver config to docker-compose
# logging:
#   driver: json-file
#   options:
#     max-size: "100m"
#     max-file: "5"
```

---

## Runbook Maintenance

| Last reviewed | Reviewer | Changes |
|---------------|----------|---------|
| 2026-08-27 | Platform Engineering | Initial creation |

**Review schedule:** Monthly or after any SEV1/SEV2 incident.

**To add a new incident type:**
1. Create entry following the template (Symptoms → Diagnosis → Resolution → Post-incident)
2. Add to table of contents
3. Create corresponding alert in monitoring
4. Notify on-call team of new runbook entry
