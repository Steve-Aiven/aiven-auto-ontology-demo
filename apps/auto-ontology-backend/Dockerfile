# Prefer building with context vendor/nvidia-auto-ontology and Dockerfile.aiven.
# This copy stays in sync for tooling that looks under apps/.
ARG BASE_IMG=ubuntu
ARG BASE_IMG_TAG=22.04
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
COPY vendor/nvidia-auto-ontology/pyproject.toml vendor/nvidia-auto-ontology/uv.lock vendor/nvidia-auto-ontology/.python-version ./
COPY vendor/nvidia-auto-ontology/vendor/ vendor/
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
COPY --chown=auto_ontology:auto_ontology vendor/nvidia-auto-ontology/auto_ontology/ ./auto_ontology/
COPY --chown=auto_ontology:auto_ontology vendor/nvidia-auto-ontology/pyproject.toml ./
RUN python -c "from auto_ontology.server.users.permissions import permissions_for_role; assert 'group:read' in permissions_for_role('admin')"
COPY --chown=auto_ontology:auto_ontology vendor/nvidia-auto-ontology/alembic/ ./alembic/
COPY --chown=auto_ontology:auto_ontology vendor/nvidia-auto-ontology/alembic.ini ./
COPY --chmod=0755 <<'EOF' /usr/local/bin/entrypoint.sh
#!/bin/sh
set -e
mode="${1:-server}"
case "$mode" in
  server)
    # Runtime has no separate migrate Job; apply schema then serve.
    alembic upgrade head
    exec python -m auto_ontology.server
    ;;
  ingestion_service) exec python -m auto_ontology.ingestion_service ;;
  migrate) exec alembic upgrade head ;;
  *) echo "Unknown mode: $mode" >&2; exit 2 ;;
esac
EOF
COPY vendor/nvidia-auto-ontology/LICENSE vendor/nvidia-auto-ontology/THIRD_PARTY_NOTICES.md vendor/nvidia-auto-ontology/CONTAINER_THIRD_PARTY_NOTICES.md vendor/nvidia-auto-ontology/OPEN_SOURCE_NOTICE /licenses/
USER auto_ontology
EXPOSE 3001
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]
CMD ["server"]
