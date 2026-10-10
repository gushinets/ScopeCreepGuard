ARG NODE_VERSION=22-bookworm-slim

FROM node:${NODE_VERSION} AS dependencies

WORKDIR /app

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

RUN printf '%s\n' 'node-linker=hoisted' > .npmrc \
  && corepack enable \
  && corepack prepare pnpm@10.34.1 --activate \
  && pnpm install --frozen-lockfile

FROM dependencies AS migrate

WORKDIR /app

COPY drizzle.config.ts ./
COPY drizzle ./drizzle
COPY lib/db ./lib/db

CMD ["pnpm", "db:migrate"]

FROM node:${NODE_VERSION} AS builder

WORKDIR /app

COPY --from=dependencies /app/node_modules ./node_modules
COPY --from=dependencies /app/package.json ./package.json
COPY --from=dependencies /app/pnpm-lock.yaml ./pnpm-lock.yaml
COPY --from=dependencies /app/.npmrc ./.npmrc
COPY . .

ARG DATABASE_URL
ENV DATABASE_URL=${DATABASE_URL}
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN if [ -z "$DATABASE_URL" ]; then \
      echo '{"event":"config_missing","variable":"DATABASE_URL","source":"Dockerfile"}'; \
      exit 1; \
    fi \
  && corepack enable \
  && corepack prepare pnpm@10.34.1 --activate \
  && pnpm build

FROM node:${NODE_VERSION} AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

COPY --from=builder --chown=node:node /app/public ./public

RUN mkdir .next && chown node:node .next

COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static
COPY --from=builder --chown=node:node /app/scripts/docker-entrypoint.mjs ./docker-entrypoint.mjs

USER node

EXPOSE 3000

CMD ["node", "docker-entrypoint.mjs"]
