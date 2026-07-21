# Integration Map

| Product slot | Repository | Required integration contract |
|--------------|------------|-------------------------------|
| Model supply chain | `poojakira/hf-model-provenance-scanner` | File/model scan request, structured findings response, health endpoint |
| MCP gateway monitoring | `poojakira/mcp-security-gateway-monitor` | Tool-call event input, detection findings, audit-event output |
| Adversarial robustness | `poojakira/adversarial-ml-lab` | Attack evaluation job input, benchmark result artifact |
| LLM redteam | `poojakira/llm-redteam-framework` | Prompt batch input, detector result output |
| Dataset poisoning | `poojakira/dataset-poisoning-detector` | Dataset sample batch input, anomaly finding output |
| Model privacy | `poojakira/model-privacy-attacks` | Attack configuration input, privacy-risk report output |
| Secure RUL forecasting | `poojakira/PulseNet-RUL-Forecasting` | Forecast request input, authenticated prediction and audit output |

No repository is vendored here. A future runnable integration layer must pin service versions and prove health checks in CI before claiming platform readiness.