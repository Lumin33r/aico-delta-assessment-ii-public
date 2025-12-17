# =============================================================================
# AI Personal Tutor - Frontend Dockerfile
# =============================================================================
# Multi-stage build for React/Vite frontend with Nginx
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder
# -----------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (better caching)
COPY package.json package-lock.json ./
RUN npm ci

# Copy source code
COPY . .

# Build arguments for environment variables (baked into build)
ARG VITE_LEX_BOT_ID
ARG VITE_LEX_BOT_ALIAS_ID
ARG VITE_AWS_REGION
ARG VITE_COGNITO_IDENTITY_POOL_ID
ARG VITE_API_URL

# Set environment variables for build
ENV VITE_LEX_BOT_ID=$VITE_LEX_BOT_ID \
    VITE_LEX_BOT_ALIAS_ID=$VITE_LEX_BOT_ALIAS_ID \
    VITE_AWS_REGION=$VITE_AWS_REGION \
    VITE_COGNITO_IDENTITY_POOL_ID=$VITE_COGNITO_IDENTITY_POOL_ID \
    VITE_API_URL=$VITE_API_URL

# Build the application
RUN npm run build

# -----------------------------------------------------------------------------
# Stage 2: Production with Nginx
# -----------------------------------------------------------------------------
FROM nginx:alpine AS production

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Create non-root user for nginx
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost:80/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
