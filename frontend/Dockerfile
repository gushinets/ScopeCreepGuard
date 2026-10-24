ARG NODE_VERSION=22-bookworm-slim
FROM node:${NODE_VERSION} AS dependencies
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN corepack enable && corepack prepare pnpm@10.34.1 --activate && pnpm install --frozen-lockfile

FROM dependencies AS builder
COPY . .
RUN pnpm build

FROM nginxinc/nginx-unprivileged:stable-alpine AS runner
ARG SOURCE_REVISION=unknown
LABEL org.opencontainers.image.revision=$SOURCE_REVISION
ENV SCOPE_GUARD_API_ORIGIN=http://backend:8000
ENV NGINX_ENVSUBST_FILTER=^SCOPE_GUARD_API_ORIGIN$
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY nginx/api-proxy.conf /etc/nginx/api-proxy.conf
COPY --chmod=755 nginx/05-validate-upstream.sh /docker-entrypoint.d/05-validate-upstream.sh
EXPOSE 3000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s CMD wget -q -O /dev/null http://127.0.0.1:3000/health/live || exit 1
