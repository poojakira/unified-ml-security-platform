# Reproduce the Work - Poster 07

**Repository:** `github.com/poojakira/unified-ml-security-platform`  
**Verified code snapshot:** `01e58ba257764e47e230a3eecd5a821bb85e7985`  
**CI/CD run:** `36783840279`

```bash
git clone https://github.com/poojakira/unified-ml-security-platform.git
cd unified-ml-security-platform
git checkout 01e58ba257764e47e230a3eecd5a821bb85e7985
python -m pip install -e ".[dev]"
pytest tests/ -q
docker compose config
docker compose -f docker-compose.prod.yml config
```

Expected core unit evidence: **67 passed**, **56.89% statement coverage**.

Interpretation rule: local stub health checks validate the gateway/topology contract only. They do not establish downstream product functionality.
