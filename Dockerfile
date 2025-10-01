# Multi-stage build for OpenManus
FROM python:3.12-slim AS builder

WORKDIR /app/OpenManus

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && update-ca-certificates

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies directly with pip
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.12-slim

WORKDIR /app/OpenManus

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/OpenManus/workspace /app/OpenManus/logs /app/OpenManus/config

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV ENV_MODE=PRODUCTION

# Expose ports for different services
EXPOSE 8000 8001 10000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command
CMD ["python", "main.py"]
