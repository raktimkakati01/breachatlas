# BreachAtlas frontend image. Multi-stage Next.js standalone build, non-root.
FROM node:26.13.1-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:26.13.1-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
# NEXT_PUBLIC_* is inlined at build time, so the API URL must be set here.
# Override for a real deploy: docker build --build-arg NEXT_PUBLIC_API_URL=https://host/api/v1
ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
RUN npm run build

FROM node:26.13.1-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000

# Run as an unprivileged user (hardening from day one).
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# The standalone output bundles a minimal server + only the needed node_modules.
COPY --from=build /app/public ./public
COPY --from=build --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000/',r=>process.exit(r.statusCode===200?0:1)).on('error',()=>process.exit(1))"

CMD ["node", "server.js"]
