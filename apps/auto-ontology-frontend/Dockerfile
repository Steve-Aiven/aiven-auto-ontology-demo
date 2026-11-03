# Runtime/local builds should use:
#   context: ./vendor/nvidia-auto-ontology/frontend
#   dockerfile: Dockerfile.aiven
# Kept for discoverability; identical public Ubuntu base as Dockerfile.aiven.
ARG NODE_MAJOR=22
ARG PNPM_VERSION=10.10.0
ARG BASE_IMG=ubuntu
ARG BASE_IMG_TAG=22.04
FROM ${BASE_IMG}:${BASE_IMG_TAG} AS base-node
ARG NODE_MAJOR
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
 && curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && apt-get purge -y --auto-remove curl gnupg \
 && rm -rf /var/lib/apt/lists/*
# Remainder lives in vendor frontend Dockerfile.aiven; compose uses that path.
WORKDIR /app
CMD ["node","-e","console.error('Build with vendor/nvidia-auto-ontology/frontend/Dockerfile.aiven'); process.exit(1)"]
