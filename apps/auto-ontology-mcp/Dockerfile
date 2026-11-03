# MCP server. Build context: repository root.
ARG PYTHON_VERSION=3.12
ARG UV_VERSION=0.11.29
ARG BASE_IMG=ubuntu
ARG BASE_IMG_TAG=22.04

FROM ${BASE_IMG}:${BASE_IMG_TAG} AS builder
ARG PYTHON_VERSION
ARG UV_VERSION
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_INSTALL_DIR=/opt/python
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" -o /tmp/install-uv.sh \
 && env UV_UNMANAGED_INSTALL=/usr/local/bin sh /tmp/install-uv.sh \
 && rm /tmp/install-uv.sh
WORKDIR /app
COPY vendor/nvidia-auto-ontology/mcp/pyproject.toml \
     vendor/nvidia-auto-ontology/mcp/uv.lock \
     vendor/nvidia-auto-ontology/mcp/README.md ./
COPY vendor/nvidia-auto-ontology/mcp/auto_ontology_mcp/ ./auto_ontology_mcp/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv python install "${PYTHON_VERSION}" \
 && uv sync --frozen --no-dev

FROM ${BASE_IMG}:${BASE_IMG_TAG} AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:${PATH}" \
    AUTO_ONTOLOGY_MCP_HOST=0.0.0.0 AUTO_ONTOLOGY_MCP_PORT=3003
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && apt-get install -y --no-install-recommends ca-certificates tini \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 1000 auto_ontology \
 && useradd --system --uid 1000 --gid auto_ontology --home /app --shell /usr/sbin/nologin auto_ontology
WORKDIR /app
COPY --from=builder /opt/python /opt/python
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder --chown=auto_ontology:auto_ontology /app /app
USER auto_ontology
EXPOSE 3003
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["auto-ontology-mcp"]
