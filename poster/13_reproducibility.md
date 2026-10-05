# Reproduce the Work - Poster 07

**Repository:** `github.com/poojakira/unified-ml-security-platform`
**Verified code snapshot:** `26aace469f65e46cbbf38525aa0a36f6eca6d53b`
**CI/CD run:** `36944325113`

```bash
git clone https://github.com/poojakira/unified-ml-security-platform.git
cd unified-ml-security-platform
git checkout 26aace469f65e46cbbf38525aa0a36f6eca6d53b
python -m pip install -e ".[dev]"
pytest tests/ -q
docker compose config
docker compose -f docker-compose.prod.yml config
```

Expected core unit evidence: **82 passed**, **95.96% statement coverage**.

Interpretation rule: local stub health checks validate the gateway/topology contract only. They do not establish downstream product functionality.
