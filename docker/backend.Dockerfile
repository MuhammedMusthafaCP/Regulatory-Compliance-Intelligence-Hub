# syntax=docker/dockerfile:1
# Build context is the REPOSITORY ROOT (see docker-compose.yml): the API reuses the retrieval
# pipeline from ingestion/, so the image needs both backend/ and ingestion/.
FROM python:3.12-slim

# HF_HUB_OFFLINE: the models are baked into the image (below), so the container never needs the network for them.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/opt/hf \
    HF_HUB_OFFLINE=1 \
    HOME=/tmp

WORKDIR /app

# Run as an unprivileged user
RUN useradd --system --uid 10001 --no-create-home appuser \
    && chown appuser /app

# Lets download steps trust an optional extra root CA (corporate TLS inspection); see docker/with-extra-ca.sh
COPY --chmod=755 docker/with-extra-ca.sh /usr/local/bin/with-extra-ca

# 1. API dependencies: this layer is only rebuilt when requirements.txt changes
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 2. Search dependencies. torch comes from PyTorch's CPU-only index: the PyPI wheels (x86_64 and, now, ARM64 too)
#    depend on ~3 GB of CUDA libraries that a container without a GPU cannot use. Everything else comes from PyPI.
#    Override TORCH_INDEX_URL to use a mirror. If this step fails with "self-signed certificate in chain", a
#    TLS-inspecting proxy (for example Cloudflare WARP) is intercepting the download: run `make ca` (README,
#    Troubleshooting). Never disable certificate verification.
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
COPY backend/requirements-search.txt ./requirements-search.txt
RUN --mount=type=secret,id=extra_ca \
    with-extra-ca sh -c 'pip install --no-cache-dir torch==2.14.1 --index-url "$0" && pip install --no-cache-dir -r requirements-search.txt' "$TORCH_INDEX_URL"

# 3. The pinned models (embedding model + reranker, ~1 GB). Only the files that define them are copied first,
#    so this layer is rebuilt when a pinned revision changes, not when other pipeline code does.
COPY ingestion/__init__.py ingestion/embedding.py ingestion/rerank.py ingestion/fetch_models.py ./ingestion/
RUN --mount=type=secret,id=extra_ca \
    HF_HUB_OFFLINE=0 with-extra-ca python -m ingestion.fetch_models \
    && chown -R appuser /opt/hf

COPY --chown=appuser backend/alembic.ini ./
COPY --chown=appuser backend/alembic ./alembic
COPY --chown=appuser ingestion ./ingestion
COPY --chown=appuser backend/app ./app

USER appuser

EXPOSE 8000
# Liveness only: the API is up while the search engine is still loading in the background
HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=10 \
    CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://localhost:8000/')"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
