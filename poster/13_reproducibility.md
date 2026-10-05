# Reproduce the Work - Poster 07

**Repository:** `github.com/poojakira/unified-ml-security-platform`
**Verified code snapshot:** `d54336b5f5f058a4d756bf2c7a023ad8510bbd6f`
**CI/CD run:** `37173681100`

```bash
git clone https://github.com/poojakira/unified-ml-security-platform.git
cd unified-ml-security-platform
git checkout d54336b5f5f058a4d756bf2c7a023ad8510bbd6f
python -m pip install -e ".[dev]"
pytest tests/ -q
docker compose config
docker compose -f docker-compose.prod.yml config
```

Expected core unit evidence: **82 passed**, **95.96% statement coverage**.

Interpretation rule: local stub health checks validate the gateway/topology contract only. They do not establish downstream product functionality.
