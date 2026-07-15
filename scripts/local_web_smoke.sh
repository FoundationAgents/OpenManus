#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SERVER_PID_FILE="/tmp/openmanus_web_smoke_server.pid"
SERVER_LOG="/tmp/openmanus_web_smoke_server.log"

cleanup() {
  if [[ -f "$SERVER_PID_FILE" ]]; then
    kill "$(cat "$SERVER_PID_FILE")" >/dev/null 2>&1 || true
    rm -f "$SERVER_PID_FILE"
  fi
}
trap cleanup EXIT

if [[ -z "${DATABASE_URL:-}" ]]; then
  export DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/openmanus"
fi

echo "[smoke] Using DATABASE_URL=$DATABASE_URL"

check_postgres_ready() {
  if command -v pg_isready >/dev/null 2>&1; then
    pg_isready -h localhost -U postgres -d openmanus >/dev/null 2>&1
    return $?
  fi

  python - <<'PY'
import os, sys
import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password="postgres",
        dbname="openmanus",
    )
    conn.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
PY
  return $?
}

echo "[smoke] Checking PostgreSQL readiness..."
pg_ready=false
for i in {1..15}; do
  if check_postgres_ready; then
    echo "[smoke] PostgreSQL is ready"
    pg_ready=true
    break
  fi
  sleep 1
done

if [[ "$pg_ready" != true ]]; then
  echo "[smoke] PostgreSQL not reachable on localhost:5432, trying to start docker compose service..."
  docker compose up -d postgres >/dev/null 2>&1 || true
fi

for i in {1..30}; do
  if check_postgres_ready; then
    echo "[smoke] PostgreSQL is ready"
    pg_ready=true
    break
  fi
  if [[ "$i" -eq 30 ]]; then
    echo "[smoke] PostgreSQL not ready in time"
    exit 1
  fi
  sleep 1
done

echo "[smoke] Starting FastAPI server..."
uvicorn server.api:app --host 0.0.0.0 --port 8000 --workers 1 >"$SERVER_LOG" 2>&1 &
echo $! >"$SERVER_PID_FILE"

# Wait for server to be ready with retries
for i in {1..30}; do
  if curl -sf http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
    echo "[smoke] Server is ready"
    break
  fi
  echo "[smoke] Waiting for server... attempt $i/30"
  sleep 1
done

echo "[smoke] Checking /api/health..."
for i in {1..10}; do
  if curl -sf http://127.0.0.1:8000/api/health >/tmp/openmanus_web_smoke_health.json; then
    cat /tmp/openmanus_web_smoke_health.json
    break
  fi
  if [[ "$i" -eq 10 ]]; then
    echo "[smoke] Health endpoint not responding"
    echo "----- server log -----"
    cat "$SERVER_LOG" || true
    exit 1
  fi
  sleep 2
done

echo "[smoke] Checking /docs..."
curl -sf http://127.0.0.1:8000/docs >/tmp/openmanus_web_smoke_docs.html
grep -i "swagger" /tmp/openmanus_web_smoke_docs.html >/dev/null

echo "[smoke] PASS"
