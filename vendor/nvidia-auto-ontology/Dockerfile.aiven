# Builds from vendored NVIDIA Auto Ontology with a public Ubuntu base
# (avoids NGC auth for nvcr.io/nvidia/base/ubuntu and unpublished app tags).
ARG BASE_IMG=ubuntu
ARG BASE_IMG_TAG=22.04
# Delegate to upstream Dockerfile with overridden base image.
# Build context MUST be vendor/nvidia-auto-ontology
FROM ${BASE_IMG}:${BASE_IMG_TAG} AS _unused
# The real build uses the upstream file; this Dockerfile exists so Runtime
# discovers apps/auto-ontology-backend/Dockerfile. Prefer:
#   docker build -f Dockerfile --build-arg BASE_IMG=ubuntu --build-arg BASE_IMG_TAG=22.04 .
# from vendor/nvidia-auto-ontology.
#
# Compose sets dockerfile to this path with context vendor/nvidia-auto-ontology
# by copying upstream content below (keep in sync with vendor Dockerfile).

ARG UV_VERSION=0.11.29
FROM ${BASE_IMG}:${BASE_IMG_TAG} AS builder
ARG UV_VERSION
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_INSTALL_DIR=/opt/python
RUN apt-get update && apt-get install -y --no-install-recommends build-essential ca-certificates curl git libpq-dev \
 && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" -o /tmp/install-uv.sh \
 && env UV_UNMANAGED_INSTALL=/usr/local/bin sh /tmp/install-uv.sh && rm /tmp/install-uv.sh
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
COPY vendor/ vendor/
RUN --mount=type=cache,target=/root/.cache/uv uv sync --no-dev --no-install-project

FROM ${BASE_IMG}:${BASE_IMG_TAG} AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:${PATH}" PORT=3001
RUN apt-get update && apt-get upgrade -y --no-install-recommends \
 && apt-get install -y --no-install-recommends ca-certificates libpq5 tini \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 1000 auto_ontology \
 && useradd --system --uid 1000 --gid auto_ontology --home /app --shell /usr/sbin/nologin auto_ontology
WORKDIR /app
COPY --from=builder /opt/python /opt/python
COPY --from=builder /opt/venv /opt/venv
COPY --chown=auto_ontology:auto_ontology auto_ontology/ ./auto_ontology/
COPY --chown=auto_ontology:auto_ontology pyproject.toml ./
RUN python -c "from auto_ontology.server.users.permissions import permissions_for_role; assert 'group:read' in permissions_for_role('admin')"
COPY --chown=auto_ontology:auto_ontology alembic/ ./alembic/
COPY --chown=auto_ontology:auto_ontology alembic.ini ./
COPY --chmod=0755 <<'EOF' /usr/local/bin/entrypoint.sh
#!/bin/sh
set -e
mode="${1:-server}"
case "$mode" in
  server) exec python -m auto_ontology.server ;;
  ingestion_service) exec python -m auto_ontology.ingestion_service ;;
  migrate) exec alembic upgrade head ;;
  *) echo "Unknown mode: $mode" >&2; exit 2 ;;
esac
EOF
COPY LICENSE THIRD_PARTY_NOTICES.md CONTAINER_THIRD_PARTY_NOTICES.md OPEN_SOURCE_NOTICE /licenses/
USER auto_ontology
EXPOSE 3001
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{__import__(\"os\").environ.get(\"PORT\",\"3001\")}/api/health/live', timeout=3).status == 200 else 1)"
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]
CMD ["server"]
