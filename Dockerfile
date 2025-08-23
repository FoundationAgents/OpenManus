FROM python:3.12-slim

WORKDIR /app/OpenManus

RUN apt-get update && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/* \
    && (command -v uv >/dev/null 2>&1 || pip install --no-cache-dir uv)

COPY . .

RUN uv pip install --system -r requirements.txt

# Expose the API server port
EXPOSE 8000

# Set environment variables for production
ENV PYTHONPATH=/app/OpenManus
ENV PYTHONUNBUFFERED=1

# Start the API server
CMD ["python", "api_server.py"]
