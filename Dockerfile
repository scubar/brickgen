# Multi-stage Dockerfile for BrickGen
# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend files
COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# Stage 2: Production image with Python backend
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    libpng16-16 \
    libjpeg62-turbo \
    && rm -rf /var/lib/apt/lists/*

# Download and install LDView OSMesa (headless version) from GitHub releases
RUN wget -q https://github.com/tcobbs/ldview/releases/download/v4.6/ldview-osmesa-4.6-debian-bookworm.amd64.deb && \
    dpkg -i ldview-osmesa-4.6-debian-bookworm.amd64.deb || true && \
    apt-get update && apt-get install -f -y && \
    rm ldview-osmesa-4.6-debian-bookworm.amd64.deb && \
    rm -rf /var/lib/apt/lists/*

# Install pipenv
RUN pip install --no-cache-dir pipenv

# Copy Pipfile only (not the placeholder lock file)
COPY backend/Pipfile ./

# Install dependencies using pipenv
# --system flag installs packages to system python (no virtualenv in container)
# --skip-lock skips lock file and installs directly from Pipfile
RUN pipenv install --system --skip-lock

# Copy backend code
COPY backend/ ./backend/

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/frontend/dist ./backend/static

# Create directories for data
RUN mkdir -p /app/data/ldraw /app/cache /app/database

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
