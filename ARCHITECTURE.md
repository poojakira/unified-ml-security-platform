# Architecture

This document specifies the target integration architecture for the ML-security portfolio.

## Target Boundary

The intended platform boundary is a thin gateway that routes authenticated requests to independently deployed product services. Each product owns its own tests, dependency policy, SBOM, and runtime configuration.

## Target Gateway

| Route | Target service | Repository |
|-------|----------------|------------|
| `/scan` | HF model scanner | `poojakira/hf-model-provenance-scanner` |
| `/monitor` | MCP security gateway | `poojakira/mcp-security-gateway-monitor` |
| `/robustness` | Adversarial ML lab | `poojakira/adversarial-ml-lab` |
| `/redteam` | LLM redteam framework | `poojakira/llm-redteam-framework` |
| `/poisoning` | Dataset poisoning detector | `poojakira/dataset-poisoning-detector` |
| `/privacy` | Model privacy attacks | `poojakira/model-privacy-attacks` |
| `/rul` | PulseNet RUL forecasting | `poojakira/PulseNet-RUL-Forecasting` |

## Non-Goals

This repository does not currently provide runnable service implementations, production deployment, or measured detection claims.