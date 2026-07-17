# Adversarial ML Lab

**Comprehensive Adversarial Robustness Evaluation Framework**

## Overview
20-tier attack surface evaluation against PyTorch models including gradient attacks, black-box queries, model stealing, LLM prompt injection, data poisoning, certified defenses, and CI-gateable robustness benchmarks.

## Attack Surface (20 Tiers)

| Tier | Modules | Coverage |
|------|---------|----------|
| **1: Foundation** | fgsm, pgd, cw, blackbox, model_stealing, norms, llm, poisoning | FGSM, PGD, C&W, SimBA/Square/HopSkipJump/Boundary, knockoff nets, L0/L1/L2/Linf/Wasserstein/semantic/patch, GCG/AutoDAN/prompt injection, BadNets/clean-label/gradient |
| **2: Adaptive** | adaptive, param_search, constrained, evasion, ensemble, inference, chaining, api_sim | BPDA + EoT, Bayesian optimization, query/compute budgets, JPEG/feature squeeze bypass, multi-model, batch/timing, multi-stage, rate limits |
| **3: Non-Classification** | non_classification.py | Detection, segmentation, regression, RL, recommenders |
| **4: Certified Eval** | certified.py (eval) | Randomized smoothing, Lipschitz, IBP |
| **5: Privacy/Physical** | inversion.py, physical.py, universal.py | Model inversion, membership inference, EOT patches, UAPs |

## API

### Run Benchmark
```bash
POST /eval/attack
{
  "model_id": "resnet18_cifar10",
  "attack": "pgd",
  "params": {"eps": 8/255, "steps": 20, "restarts": 5},
  "dataset": "cifar10",
  "batch_size": 128
}
```

**Response:**
```json
{
  "model": "resnet18_cifar10",
  "clean_accuracy": 0.95,
  "robust_accuracy": {"pgd": 0.52},
  "epsilon": 8/255,
  "pgd_gate_passed": true
}
```

### AutoAttack
```bash
POST /eval/autoattack
{
  "model_id": "resnet18_cifar10",
  "version": "standard",
  "eps": 8/255
}
```

### Certified Evaluation
```bash
POST /eval/certified
{
  "model_id": "smoothed_resnet",
  "method": "smoothing",
  "sigma": 0.25
}
```

## CI/CD Integration

```yaml
# .github/workflows/robustness.yml
- name: Robustness Gate
  run: |
    python -m adv_lab.eval.harness \
      --model models/best.pt \
      --dataset cifar10 \
      --attacks pgd,cw,autoattack \
      --eps 8/255 \
      --gate-threshold 0.30 \
      --output results/robustness.json
```

### Gate Configuration
```json
{
  "gates": {
    "pgd_robust": {"min": 0.30, "attack": "pgd", "eps": "8/255"},
    "cw_robust": {"min": 0.20, "attack": "cw"},
    "autoattack": {"min": 0.25, "attack": "autoattack"},
    "union_robust": {"min": 0.15, "norms": ["linf", "l2", "l1"]}
  }
}
```

## HMAC-Signed Results

```python
# Results include HMAC for tamper-evidence
{
  "results": {...},
  "hmac": "sha256=...",
  "key_id": "ci-gate-key-2024"
}
```

Verify in CI:
```bash
python -m adv_lab.eval.ci_signing verify results/robustness.json --hmac-key-env ADV_LAB_HMAC_KEY
```

## Certified Defenses

### Randomized Smoothing
```python
from adv_lab.defenses.certified import RandomizedSmoothing

smoothed = RandomizedSmoothing(base_model, sigma=0.25, n_samples=1000)
certified_radius = smoothed.certify(x, n0=100, n=10000, alpha=0.001)
```

### Interval Bound Propagation
```python
from adv_lab.defenses.certified import IBP

ibp_model = IBP(model, eps=8/255)
certified_acc = ibp_model.certified_accuracy(test_loader)
```

## RobustBench Integration

```bash
# Download pretrained robust models
python -m adv_lab.robustbench download --model cifar10 --eps 8/255

# Evaluate against RobustBench leaderboard
python -m adv_lab.eval.robustbench --model models/robust_resnet.pt
```

## SOTA Defenses Implemented

| Defense | Paper | Implementation |
|---------|-------|----------------|
| PGD-AT (7-step) | Madry et al. 2018 | `adversarial_training.py` |
| TRADES | Zhang et al. 2019 | `adversarial_training.py` |
| MART | Wang et al. 2020 | `adversarial_training.py` |
| AWP | Wu et al. 2020 | `adversarial_training.py` |
| HEAT | Cheng et al. 2023 | `adversarial_training.py` |
| GAT | Zhang et al. 2021 | `adversarial_training.py` |

## Distributed Adversarial Training

```python
# Multi-GPU PGD-AT with DDP
torchrun --nproc_per_node=4 -m adv_lab.distributed.train \
  --model resnet18 --dataset cifar10 \
  --attack pgd --steps 7 --eps 8/255 \
  --mixed-precision --grad-accum 2
```

## Requirements

```
fastapi==0.109.0
uvicorn==0.27.0
httpx==0.27.0
pydantic==2.6.0
pydantic-settings==2.1.0
torch==2.2.0
torchvision==0.17.0
numpy==1.26.0
scipy==1.12.0
scikit-learn==1.4.0
xgboost==2.0.0
rich==13.7.0
prometheus-client==0.19.0
psutil==5.9.0
watchdog==4.0.0
```

## Architecture

```
adv_ml/
├── attacks/
│   ├── fgsm.py, pgd.py, cw.py
│   ├── blackbox.py
│   ├── model_stealing.py
│   ├── llm.py
│   ├── poisoning.py
│   ├── adaptive.py
│   ├── param_search.py
│   ├── constrained.py
│   ├── evasion.py
│   ├── ensemble.py
│   ├── inference.py
│   ├── chaining.py
│   ├── api_sim.py
│   ├── non_classification.py
│   ├── physical.py
│   └── universal.py
├── defenses/
│   ├── adversarial_training.py
│   └── detection.py
├── eval/
│   ├── harness.py
│   ├── transferability.py
│   ├── certified.py
│   └── ci_signing.py
└── server.py
```

## License

Apache 2.0