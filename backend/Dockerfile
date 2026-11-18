# ============================================
# AVON-1 BEAST - Production Dockerfile
# ============================================
# Multi-stage build for optimized production image

# Stage 1: Build dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
COPY requirements-*.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Production image
FROM python:3.11-slim as production

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash avon && \
    mkdir -p /app/data /app/logs && \
    chown -R avon:avon /app

# Copy application code (excluding files in .dockerignore)
COPY --chown=avon:avon . .

# Ensure .env is NOT present in the container
RUN rm -f .env .env.*

# Switch to non-root user
USER avon

# Environment variables with production defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BEAST_LOG_LEVEL=INFO

# Set the entrypoint to the CLI wrapper
ENTRYPOINT ["python", "cli.py"]
CMD ["--help"]
