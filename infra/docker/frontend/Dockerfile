# =============================================================================
# Auto Code Frontend - Development Dockerfile
# =============================================================================

FROM node:22-alpine

# Set working directory
WORKDIR /app/frontend

# Copy package files for dependency installation
COPY frontend/package.json frontend/package-lock.json* frontend/yarn.lock* frontend/pnpm-lock.yaml* ./

# Install dependencies
RUN if [ -f pnpm-lock.yaml ]; then \
        corepack enable && pnpm install --frozen-lockfile; \
    elif [ -f yarn.lock ]; then \
        yarn install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then \
        npm ci; \
    else \
        npm install; \
    fi

# Copy source code
COPY frontend/ .

EXPOSE 3000

# Set Next.js telemetry opt-out
ENV NEXT_TELEMETRY_DISABLED=1

# Development server with hot reload
CMD ["npm", "run", "dev"]
