# Dataset Poisoning Detector

**Training Data Integrity & Anomaly Detection for ML Pipelines**

## Overview
Detects poisoned/backdoored samples in training datasets using ensemble anomaly detection. Surfaces suspicious samples for human review — does not claim to prove poisoning occurred without external evidence.

## Detection Methods (Ensemble)

| Method | Mechanism | Strengths | Weaknesses |
|--------|-----------|-----------|------------|
| **Z-score** | Features > Nσ from mean | Fast, interpretable | Assumes normality; blind to in-distribution |
| **IQR Fencing** | Robust stats (1.5×IQR) | Not skewed by outliers | Hard boundary; smart attackers stay inside |
| **Isolation Forest** | Random split depth | Catches density anomalies | Black box; degrades in high-dim |

**Ensemble (Default):** Majority vote across all 3 → 2/3 agreement required

## Attack Coverage

| Attack Type | Detection | Notes |
|-------------|-----------|-------|
| Label flip (random) | ✅ High | Feature distribution shift |
| Label flip (targeted) | ⚠️ Medium | Requires sufficient poison rate |
| Clean-label (feature) | ⚠️ Low | Features look normal; label correct |
| Backdoor/Trigger | ✅ Medium | Trigger creates feature anomaly |
| Distributed/Stealth | ❌ Low | Each sample looks normal individually |
| Feature mimicry | ❌ Low | Adversarial crafting defeats stats |

## Honest Performance (CIFAR-10 Label Flip)

| Flip Rate | AUC | FPR @ 5% target | TPR |
|-----------|-----|-----------------|-----|
| 5% | 0.55 | 5.0% | 9% |
| 10% | 0.54 | 4.8% | 7% |
| 25% | 0.53 | 4.9% | 6% |

**Key Finding:** AUC barely above random (0.5). FPR ≈ target (5%) — honest calibration. **Not a silver bullet.**

## API

### Batch Detection
```bash
POST /detect/batch
Content-Type: application/json

{
  "samples": [
    {"features": [0.1, 0.8, 0.2, 0.9], "label": 1},
    {"features": [9.9, 0.0, 9.8, 0.1], "label": 0}
  ],
  "method": "ensemble"
```

**Response:**
```json
{
  "total_samples": 2,
  "poisoned_count": 1,
  "poisoned_indices": [1],
  "per_sample": [
    {"sample_idx": 0, "is_poisoned": false, "anomaly_score": 0.23, "method_votes": {"zscore": false, "iqr": false, "isolation": false}},
    {"sample_idx": 1, "is_poisoned": true, "anomaly_score": 0.91, "method_votes": {"zscore": true, "iqr": true, "isolation": true}}
  }
}
```

### Real-time Streaming (v0.2+)
```python
from dataset_poisoning import StreamingDetector, ConceptDriftDetector, SampleFingerprinter

detector = StreamingDetector(window_size=10000, contamination=0.05)
drift = ConceptDriftDetector(sensitivity=0.01)
fingerprinter = SampleFingerprinter(similarity_threshold=0.95)

for sample in data_stream:
    result = detector.score_sample(sample)
    drift.update(sample)
    
    if result.is_poisoned or fingerprinter.is_duplicate(sample):
        quarantine(sample, result)
    else:
        fingerprinter.add_sample(sample)
        pass_to_training(sample)
    
    if drift.is_drifting():
        alert("Concept drift detected - possible coordinated poisoning")
```

### Architecture
```
                          +------------------+
                          |  Data Sources    |
                          |  (S3, API, DB)   |
                          +--------+---------+
                                   |
                                   v
                    +------------------+      +------------------+
                    |  Kafka/Redis     | ---> | StreamingDetector|
                    |  Input Queue     |      |                  |
                    +------------------+      |  - Welford stats |
                    |                    |      |  - IsoForest   |
                    |                    |      |  - Drift detect|
                    |                    |      |  - Fingerprint |
                    |                    |      +-------+--------+
                    |                    |              |
                    v                    v              v
           +------------------+  +------------------+  +------------------+
           |  Clean Samples   |  |  Quarantine      |  |  Alert/Metrics   |
           |  (to training)   |  |  (human review)  |  |  (Prometheus)    |
           +------------------+  +------------------+  +------------------+
```

## When NOT to Use Real-Time Mode

| Scenario | Reason |
|----------|--------|
| **Static data** | Use batch `detect()` instead — simpler, faster |
| **< 1,000 samples** | Statistical methods need meaningful baseline |
| **Latency < 10µs** | Streaming adds ~80µs/sample overhead |
| **Trusted source only** | No external contributors = no poisoning surface |
| **Human-in-loop already** | Automated detection adds marginal value |

## Limitations (Honest)

1. **No zero false positives** — 5% FPR at 5% target by design
2. **Clean-label blind** — Attacker matches feature distribution
3. **Distributed stealth** — Each sample normal, aggregate malicious
3. **High-dim masking** — Isolation Forest degrades >100 features
4. **Not a prevention** — Detection only; needs human + retraining

## Streaming Architecture (v0.2+)

```python
from dataset_poisoning import StreamingDetector, ConceptDriftDetector, SampleFingerprinter

detector = StreamingDetector(window_size=10000, contamination=0.05)
drift = ConceptDriftDetector(sensitivity=0.01)
fingerprinter = SampleFingerprinter(similarity_threshold=0.95)

async def process_stream(data_stream):
    for sample in data_stream:
        result = detector.score_sample(sample)
        drift.update(sample)
        
        if result.is_poisoned or fingerprinter.is_duplicate(sample):
            await quarantine(sample, result)
        else:
            fingerprinter.add_sample(sample)
            await pass_to_training(sample)
        
        if drift.is_drifting():
            await alert("Concept drift detected - possible coordinated poisoning")
```

## Integration Points

| System | Integration |
|--------|-------------|
| **Kafka** | `pip install kafka-python` |
| **Redis Streams** | `pip install redis` |
| **SageMaker** | Preprocessing step |
| **Airflow** | `PythonOperator` + DAG |
| **Spark** | `mapPartitions` + broadcast model |

## Docker Deployment

```bash
docker build -t dataset-poison-detector -f Dockerfile.dataset_poison .
docker run -p 8005:8005 -v ./logs:/app/logs dataset-poison-detector
```

## Requirements

```
fastapi==0.109.0
uvicorn==0.27.0
scikit-learn==1.4.0
numpy==1.26.0
scipy==1.12.0
pandas==2.3.0
pytest==8.2.0
pytest-asyncio==0.23.0
fastapi==0.139.2
uvicorn==0.30.0
pydantic==2.14.2
pydantic-settings==2.14.2
httpx==0.28.1
pydantic-settings==2.14.2
python-dotenv==1.0.1
prometheus-client==0.25.0
redis==5.2.0
websockets==13.1
```

## License

Apache 2.0