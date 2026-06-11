# ============================================================
# Frontend Dockerfile
# Context: ../.. (E:\Exploit_1)
# Multi-stage: Vite build → Nginx serve
# ============================================================

# Stage 1: Build - compile React app
FROM node:18-alpine AS build

WORKDIR /build
COPY web_app/frontend/package*.json ./
RUN npm ci

COPY web_app/frontend/ ./
RUN npm run build

# Stage 2: Serve - Nginx with SPA support
FROM nginx:alpine AS runtime

# Copy built assets
COPY --from=build /build/dist /usr/share/nginx/html

# Copy Nginx config
COPY web_app/frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
