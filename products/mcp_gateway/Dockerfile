FROM python:3.12-slim

WORKDIR /app
COPY spec_service.py ./spec_service.py
COPY products/mcp_gateway/README.md ./README.md

RUN groupadd -r mlsec && useradd -r -g mlsec mlsec
USER mlsec

ENV SERVICE_NAME=mcp_gateway
ENV PORT=8002
EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8002/health', timeout=5).read()" || exit 1

CMD ["python", "spec_service.py"]