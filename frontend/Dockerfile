# Build from the frontend/ folder:
#   docker build -t nba-analytics-web frontend
#   docker run -p 3000:3000 -e API_URL=http://host.docker.internal:8000 nba-analytics-web
# The build never calls the API; pages fetch from API_URL at request time.

FROM node:24-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund


FROM node:24-slim AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1 STANDALONE=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build


# --- Runtime: the standalone server only (no node_modules from the build) -----------------------------
FROM node:24-slim
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0 API_URL=http://api:8000

COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static

USER node
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
    CMD node -e "fetch('http://127.0.0.1:' + process.env.PORT + '/').then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"

CMD ["node", "server.js"]
