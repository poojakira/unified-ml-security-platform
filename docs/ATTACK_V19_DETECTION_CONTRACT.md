# ATT&CK v19 Detection Contract

Version target: MITRE ATT&CK v19, released April 28, 2026.

Source of truth: MITRE ATT&CK Enterprise, Mobile, and ICS matrices. The local
detector in `attacks/attack_v19_detector.py` is a dependency-free seed detector
and output contract. It is not evidence that this repository has trained a full
model over every ATT&CK object.

## Required Output

Every suspicious signal must emit:

| Field | Requirement |
|-------|-------------|
| Tactic | ATT&CK tactic name and tactic ID where ATT&CK defines an ID |
| Technique | Technique name and T-ID |
| Sub-technique | Sub-technique name and T-ID.xxx, or `None` |
| Matrix | `Enterprise`, `Mobile`, or `ICS` |
| Confidence | `High`, `Medium`, or `Low` |
| Evidence | Exact quote or indicator from the analyzed input |
| Recommended action | Immediate mitigation step |

Clean input must return:

```text
No ATT&CK techniques detected. Scope covered: [Enterprise, Mobile, ICS tactics checked]
```

## Coverage Boundary

The contract covers all three ATT&CK matrices at the scope level:

| Matrix | Scope |
|--------|-------|
| Enterprise | 15 tactics, including Stealth TA0005 and Defense Impairment TA0112 |
| Mobile | 12 tactics |
| ICS | 12 tactics |

The seed rules intentionally cover common portfolio-relevant signals first:
phishing, script execution, model supply-chain compromise, persistence,
credential dumping, discovery, lateral movement, C2, exfiltration, ransomware,
mobile credential/data collection, and ICS discovery/control changes.

Full production coverage requires ingesting the official MITRE CTI STIX data for
Enterprise, Mobile, and ICS and mapping product telemetry to every applicable
technique and sub-technique. Do not market this as a fully trained ATT&CK model
until that ingestion and validation exists.

## CLI

```powershell
py -3.12 attacks\attack_v19_detector.py sample.log
py -3.12 attacks\attack_v19_detector.py sample.log --format json
Get-Content sample.log | py -3.12 attacks\attack_v19_detector.py
```

## Product Integration

Use this detector contract as the shared interface for all seven products:

| Product | ATT&CK mapping use |
|---------|--------------------|
| `hf-model-provenance-scanner` | Model artifact execution and software supply-chain signals |
| `mcp-security-gateway-monitor` | Prompt/tool exfiltration, C2-like callbacks, defense bypass attempts |
| `adversarial-ml-lab` | ML attack behavior labeling and evaluation reports |
| `llm-redteam-framework` | Prompt attack evidence and technique chaining |
| `dataset-poisoning-detector` | Poisoning campaign indicators and impact context |
| `model-privacy-attacks` | Credential, collection, and exfiltration-style privacy risk reporting |
| `PulseNet-RUL-Forecasting` | ICS-like sensor, PLC, alarm, and process-control detections |
