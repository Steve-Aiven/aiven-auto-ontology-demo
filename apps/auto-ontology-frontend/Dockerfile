# Frontend image for Aiven Runtime. Build context: repository root.
# Mirrors vendor/nvidia-auto-ontology/frontend/Dockerfile.aiven with root-relative COPY paths,
# plus migrate-on-start so Runtime does not need a separate migrate Job.
ARG NODE_MAJOR=22
ARG PNPM_VERSION=10.10.0
ARG BASE_IMG=ubuntu
ARG BASE_IMG_TAG=22.04
ARG PYTHON_API_URL=http://auto-ontology:3001

FROM ${BASE_IMG}:${BASE_IMG_TAG} AS base-node
ARG NODE_MAJOR
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
 && curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && apt-get purge -y --auto-remove curl gnupg \
 && rm -rf /var/lib/apt/lists/*

FROM base-node AS deps
ARG PNPM_VERSION
ENV PNPM_HOME=/pnpm \
    PATH=/pnpm:$PATH \
    CI=1
RUN npm install -g --silent corepack@latest \
 && corepack enable \
 && corepack prepare pnpm@${PNPM_VERSION} --activate
WORKDIR /app
COPY vendor/nvidia-auto-ontology/frontend/package.json \
     vendor/nvidia-auto-ontology/frontend/pnpm-lock.yaml \
     vendor/nvidia-auto-ontology/frontend/pnpm-workspace.yaml \
     vendor/nvidia-auto-ontology/frontend/.npmrc ./
COPY vendor/nvidia-auto-ontology/frontend/prisma ./prisma
RUN --mount=type=cache,id=pnpm-store,target=/pnpm/store \
    pnpm install --frozen-lockfile

FROM base-node AS builder
ARG PYTHON_API_URL
ARG PNPM_VERSION
ENV PNPM_HOME=/pnpm \
    PATH=/pnpm:$PATH \
    CI=1 \
    NEXT_TELEMETRY_DISABLED=1 \
    NEXT_OUTPUT=standalone \
    PYTHON_API_URL=${PYTHON_API_URL}
RUN npm install -g --silent corepack@latest \
 && corepack enable \
 && corepack prepare pnpm@${PNPM_VERSION} --activate
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY vendor/nvidia-auto-ontology/frontend/ ./
RUN pnpm build

FROM base-node AS runtime
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
RUN apt-get update \
 && apt-get install -y --no-install-recommends tini ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 1001 nodejs \
 && useradd --system --uid 1001 --gid nodejs --home /app --shell /usr/sbin/nologin nextjs
WORKDIR /app
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone/ ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./app/.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./app/public
COPY --from=builder --chown=nextjs:nodejs /app/prisma /app/migrate/prisma
COPY --from=builder --chown=nextjs:nodejs /app/prisma.config.ts /app/migrate/prisma.config.ts
COPY --from=builder --chown=nextjs:nodejs /app/prisma/migrate.sh /app/migrate/migrate.sh
RUN cd /app/migrate \
 && echo '{"name":"auto-ontology-migrate","version":"0.0.1","private":true,"dependencies":{"prisma":"7.7.0","dotenv":"17.4.2"},"overrides":{"deepmerge-ts":"^8.0.2","mysql2":"^3.22.0"}}' > package.json \
 && npm install --omit=dev --no-audit --no-fund --no-package-lock \
 && chmod +x /app/migrate/migrate.sh \
 && chown -R nextjs:nodejs /app/migrate \
 && rm -rf /usr/lib/node_modules/npm /usr/lib/node_modules/corepack \
           /usr/bin/npm /usr/bin/npx /usr/bin/corepack /root/.npm
COPY --chmod=0755 <<'EOF' /usr/local/bin/frontend-entrypoint.sh
#!/bin/sh
set -e
if [ -n "${POSTGRES_HOST:-}" ] || [ -n "${DATABASE_URL:-}" ]; then
  (cd /app/migrate && sh ./migrate.sh) || echo "frontend migrate warning: continuing"
fi
exec node app/server.js
EOF
USER nextjs
EXPOSE 3000
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/frontend-entrypoint.sh"]
