# syntax=docker/dockerfile:1
FROM node:20-alpine

ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /app
# Run as the unprivileged user shipped with the node image
RUN chown node:node /app

# Dependencies first so this layer is only rebuilt when package*.json changes
COPY --chown=node:node package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --ignore-scripts

COPY --chown=node:node next.config.mjs tailwind.config.ts postcss.config.mjs tsconfig.json next-env.d.ts .env.local ./
COPY --chown=node:node app ./app

USER node

EXPOSE 4001
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=10 \
    CMD wget -q --spider http://localhost:4001/ || exit 1
CMD ["npm", "run", "dev"]
