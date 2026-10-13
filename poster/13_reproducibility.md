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


## Claim audit and rendered-source boundary, October 13, 2026 UTC

The reviewed printed claims, source and test commit anchors, CI dates and benchmark limitations are in `verified_claims.json`. The PDF is generated from that manifest and the PNG is rasterized from the same page by `render_poster.py`. Source inventory, dated CI and separate reported experiments must not be combined into one result. Earlier artifact versions remain in Git history; these corrections do not assert production readiness.

Offline poster rendering: `python -m pip install reportlab==4.4.9 PyMuPDF==1.26.6`, then `python poster/render_poster.py`. The font is bundled with the pinned ReportLab package; no browser or network fetch is used during rendering.
