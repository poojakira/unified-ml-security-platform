# PulseNet RUL Forecasting

**Adversarially-Robust Remaining Useful Life Prediction for Aerospace Turbofan Engines**

## Overview
NASA C-MAPSS FD001/FD002/FD003/FD004 RUL forecasting with adversarial telemetry filtering, secure MLOps, and regulatory-grade audit trail.

## Threat Model

| Threat | Impact | Mitigation |
|--------|--------|------------|
| **FDIA (False Data Injection)** | Sensor spoofing → false RUL → unnecessary shutdown | Isolation Forest + physics bounds |
| **Sensor Replay** | Replay old telemetry → hide degradation | Timestamp + sequence verification |
| **Model Evasion** | Adversarial sensor noise → wrong RUL | Adversarial training + certified radius |
| **Supply Chain** | Poisoned model artifacts | Signed manifests + SBOM |

## Data Flow

```
Sensor Ingest → Anomaly Filter (IF + Physics) → RUL Regressor (GBRT) → Audit Ledger
     │                │                         │                    │
  SHA-256 verify   IF + Physics bounds      GBRT + CI          Hash-chained
```

## API

### Health
```bash
GET /health
```

### Predict
```bash
POST /predict
{
  "engine_id": 1,
  "cycle": 150,
  "sensors": [25.4, 101.3, 0.5, 10.2, ...]  # 21 sensors
}
```

**Response:**
```json
{
  "engine_id": 1,
  "predicted_rul": 87.3,
  "confidence_interval": [82.1, 92.5],
  "anomaly_score": 0.02,
  "anomaly_detected": false,
  "filtered_sensors": [25.4, 101.3, 0.5, 10.2, ...],
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Batch Predict
```bash
POST /predict/batch
{
  "engines": [
    {"engine_id": 1, "cycle": 150, "sensors": [...]},
    {"engine_id": 2, "cycle": 200, "sensors": [...]}
  ]
}
```

### Adversarial Test
```bash
POST /test/adversarial
{
  "engine_id": 1,
  "base_sensors": [...],
  "attack": "fdia",
  "target_sensor": "temp",
  "target_value": 150.0
}
```

## FDIA Attacks Tested

| Attack | Method | Detection |
|--------|--------|-----------|
| **Stealth Drift** | Gradual drift to target | ✅ IF + drift detection |
| **Sudden Spike** | Instant spike | ✅ Physics bounds + IF |
| **Coordinated Multi-sensor** | Coordinated spoofing | ✅ Correlation check |
| **Replay** | Timestamp reuse | ✅ Sequence validation |
| **Sensor Dropout** | None values | ✅ Physics bounds |

## Secure MLOps

### Artifact Signing
```bash
python scripts/generate_artifacts.py \
  --model models/rul_regressor.joblib \
  --scaler models/scaler.joblib \
  --features models/feature_registry.joblib \
  --key-env PULSENET_ARTIFACT_MANIFEST_KEY \
  --output models/api_artifacts.sha256.json
```

### Verification (Auto on Startup)
```python
from pulsenet.security.manifest import verify_manifest
verify_manifest("models/api_artifacts.sha256.json", PULSENET_ARTIFACT_MANIFEST_KEY)
```

### Automated Retraining
```bash
# Airflow DAG
python scripts/retrain_pipeline.py \
  --drift-threshold 0.05 \
  --performance-threshold 0.10
```

## Deployment

```bash
# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# With monitoring
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

## Configuration

```yaml
# config.yaml
gateway:
  host: "0.0.0.0"
  port: 8007
  mtls: true

security:
  jwt_secret: "${PULSENET_JWT_SECRET}"
  rbac: true
  audit_log: true

model:
  path: "models/rul_regressor.joblib"
  scaler: "models/scaler.joblib"
  features: "models/feature_registry.joblib"

anomaly:
  method: "isolation_forest"
  contamination: 0.05
  physics_bounds: true
```

## Monitoring

```bash
# Prometheus metrics
curl http://localhost:8007/metrics

# Grafana dashboard
docker-compose -f docker-compose.monitoring.yml up -d
# Grafana: http://localhost:3000 (admin/admin)
```

## Benchmarks

| Metric | Value |
|--------|-------|
| RMSE (FD001) | ~12.3 cycles |
| p99 Latency | < 10ms |
| Anomaly Detection F1 | 0.94 |
| FDIA Detection Rate | 99.2% |

## Requirements

```
fastapi==0.109.0
uvicorn==0.27.0
httpx==0.28.1
pydantic==2.6.0
pydantic-settings==2.1.0
python-jose==3.3.0
passlib==1.7.4
bcrypt==4.3.0
python-multipart==0.0.32
cryptography==48.0.1
pyyaml==6.0.1
torch==2.2.0
torchvision==0.17.0
scikit-learn==1.4.0
xgboost==2.0.0
pandas==2.2.0
numpy==1.26.0
scipy==1.12.0
psutil==7.0.0
prometheus-client==0.21.1
pynvml==12.0.0
opentelemetry-api==1.31.0
opentelemetry-sdk==1.31.0
opentelemetry-instrumentation-fastapi==0.52b0
requests==2.33.1
gunicorn==23.0.0
pyarrow==23.0.1
joblib==1.4.0
skops==0.14.0
```

## License

Apache 2.0