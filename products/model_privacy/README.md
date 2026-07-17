# Model Privacy Attacks

**Membership Inference & Model Extraction Evaluation Toolkit**

## Overview
Research toolkit for measuring privacy leakage from ML models: membership inference attacks (MIA), model extraction, and LLM pretraining detection (Min-K% Prob).

## Attack Coverage

| Attack | Method | Target |
|--------|--------|--------|
| **Direct MIA** | Threshold on true-class confidence | Classifiers |
| **Shadow MIA** | 4+ shadow models + meta-classifier | Any classifier |
| **Model Extraction** | Query → substitute training | Any model |
| **LLM MIA (Min-K% Prob)** | Per-token log-prob statistics | Causal LMs |

## Threat Model

| Attack | Knowledge | Queries | Use Case |
|--------|-----------|---------|----------|
| Direct MIA | Target model access | White-box | Audit own model |
| Shadow MIA | Public data + API | Black-box | Third-party audit |
| Extraction | API access | 1K-10K queries | IP theft simulation |
| Min-K% | Log-probs only | Black-box | LLM pretraining audit |

## Measured Performance (Synthetic, Seed 42)

| Attack | Metric | Value | Setup |
|--------|--------|-------|-------|
| Direct MIA | ROC AUC | **0.7709** | RF target (100 trees), 1K/1K member/non-member |
| Shadow MIA | ROC AUC | **0.7680** | RF target + 4 RF shadows |
| Extraction | Agreement | **0.892** | RF target, DT substitute, 2K queries |
| Min-20% Prob | ROC AUC | **0.9599** | Synthetic log-probs, 100/100 texts |

**Honest Disclosure:** All metrics on **synthetic data (seed 42)**. Measures implementation correctness, NOT real-world privacy leakage. For real models: WikiMIA (GPT-NeoX-20B ≈ 0.69 AUC) — not reproduced here (requires model downloads).

## API

### Direct MIA
```bash
POST /attack/mia/direct
{
  "model_id": "target-model",
  "member_samples": [...],
  "nonmember_samples": [...]
}
```

### Shadow MIA
```bash
POST /attack/mia/shadow
{
  "model_id": "target-model",
  "public_data": [...],
  "shadow_count": 4
}
```

### Model Extraction
```bash
POST /attack/extract
{
  "model_id": "target-model",
  "query_budget": 2000,
  "substitute_arch": "DecisionTree"
}
```

### LLM Min-K% Prob
```bash
POST /attack/mink
{
  "text": "The quick brown fox...",
  "token_log_probs": [-0.1, -0.5, -2.3, ...],
  "k_percent": 0.2
}
```

### Min-K% Demo
```bash
python examples/llm_mia_demo.py          # Synthetic log-probs
python examples/llm_mia_demo.py --real   # Real GPT-2 (needs transformers)
```

## Regulatory Compliance

| Regulation | Requirement | Support |
|------------|-------------|---------|
| **EU AI Act Art. 10** | Data governance + MIA testing | ✅ MIA pipeline |
| **GDPR Art. 25** | Data protection by design | ✅ Privacy budgets |
| **NIST AI RMF** | GOVERN-1.6, MAP, MEASURE | ✅ Metrics + reports |
| **HIPAA** | PHI leakage detection | ✅ MIA on medical models |

## Metrics Output (for Compliance Reports)

```json
{
  "direct_mia": {"roc_auc": 0.7709, "accuracy": 0.698},
  "shadow_mia": {"roc_auc": 0.7680, "accuracy": 0.6905},
  "extraction": {"agreement": 0.892},
  "llm_mia_mink": {"roc_auc": 0.9599, "tpr_at_1pct_fpr": 0.47},
  "disclaimer": "Synthetic seed-42 metrics. Not real-world privacy guarantees."
}
```

## Differential Privacy Integration

```bash
# Train with DP-SGD
pip install opacus
python -m model_privacy.train_dp --epsilon 1.0 --delta 1e-5

# Privacy accounting (RDP)
from model_privacy.privacy import RDPAccountant
accountant = RDPAccountant()
accountant.step(noise_multiplier=1.0, sample_rate=0.01)
epsilon = accountant.get_epsilon(delta=1e-5)
```

## PATE Framework (Private Aggregation)

```python
from model_privacy.pate import PATE

pate = PATE(n_teachers=10, student_model=student)
pate.train(teachers_data, student_data)
# Student learns with formal (ε, δ)-DP guarantee
```

## Synthetic Data Generation (DP-GAN)

```bash
pip install model_privacy[gan]
python -m model_privacy.dp_gan --epsilon 1.0 --dataset adult
```

## Compliance Reporting

```bash
# Generate EU AI Act Art. 10 report
python -m model_privacy.report --model production_model --output eu_ai_act_report.json

# NIST AI RMF GOVERN-1.6
python -m model_privacy.report --model production_model --framework nist_rmf
```

## Requirements

```
numpy<3,>=1.21
scikit-learn<2,>=1.0
pytest>=7.0
transformers>=4.38.0 (optional, for --real LLM demo)
torch>=2.3.0 (optional)
opacus>=1.5.0 (optional, for DP-SGD)
xgboost>=2.0.0 (optional, for attack classifier)
```

## Reproducibility

```bash
# All metrics deterministic (seed=42)
pytest tests/test_privacy_attacks.py -v

# Regenerates exact same numbers
python -m model_privacy.tests.test_privacy_attacks
```

## License

Apache 2.0