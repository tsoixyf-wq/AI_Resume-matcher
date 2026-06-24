# =============================================================================
# Multi-stage Docker build for Next.js frontend
# =============================================================================
# Stage 1: Install dependencies (leveraged for npm ci caching)
# Stage 2: Build the Next.js standalone output
# Stage 3: Production runtime (minimal, no devDeps)
# =============================================================================

# ---- Stage 1: Dependencies ----
FROM node:20-alpine AS deps
WORKDIR /app

# Copy package files first for layer caching
COPY package.json package-lock.json* ./
RUN npm ci --legacy-peer-deps --omit=dev

# ---- Stage 2: Builder ----
FROM node:20-alpine AS builder
WORKDIR /app

# Build-time arg for API host (used in next.config.js rewrites)
ARG NEXT_PUBLIC_API_HOST=backend
ENV NEXT_PUBLIC_API_HOST=$NEXT_PUBLIC_API_HOST

COPY package.json package-lock.json* ./
RUN npm ci --legacy-peer-deps

COPY . .

# Enable standalone output in next.config.js for Docker deployment
ENV DOCKER_BUILD=1

# Next.js build — produces .next/standalone/
RUN npm run build

# ---- Stage 3: Production Runtime ----
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy only the standalone output from the builder
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

CMD ["node", "server.js"]
