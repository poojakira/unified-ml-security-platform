# Verified Metrics - Poster 07

**Code snapshot:** `d54336b5f5f058a4d756bf2c7a023ad8510bbd6f`
**CI/CD run:** https://github.com/poojakira/unified-ml-security-platform/actions/runs/37173681100

| Metric | Verified snapshot value |
|---|---:|
| Core Python tests passed | **82** |
| Core statement coverage | **95.96%** |
| Production synchronous service slots | **4** |
| Local product topology | **Contract stubs** |
| Production product images | **Externally supplied; stubs not published** |

The cited CI/CD snapshot also validates contract-stub health, integration topology, security/dependency scanning, image build/push, and production Compose configuration.


## Claim audit and rendered-source boundary, October 13, 2026 UTC

The reviewed printed claims, source and test commit anchors, CI dates and benchmark limitations are in `verified_claims.json`. The PDF is generated from that manifest and the PNG is rasterized from the same page by `render_poster.py`. Source inventory, dated CI and separate reported experiments must not be combined into one result. Earlier artifact versions remain in Git history; these corrections do not assert production readiness.

Offline poster rendering: `python -m pip install reportlab==4.4.9 PyMuPDF==1.26.6`, then `python poster/render_poster.py`. The font is bundled with the pinned ReportLab package; no browser or network fetch is used during rendering.
