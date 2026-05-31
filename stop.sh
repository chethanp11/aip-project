#!/usr/bin/env bash
if [ -z "${BASH_VERSION:-}" ]; then
  exec /usr/bin/env bash "$0" "$@"
fi
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$REPO_ROOT/Infra/docker"
PORT="${PORT:-8000}"

echo "==================================="
echo "STOPPING AIP PLATFORM"
echo "==================================="

# 1. Stop the active FastAPI / Uvicorn Server
echo ""
echo "===== STOPPING APPLICATION SERVER ====="
existing_pids="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"
if [ -n "$existing_pids" ]; then
  for existing_pid in $existing_pids; do
    existing_cmd="$(ps -p "$existing_pid" -o command= 2>/dev/null || true)"
    if [[ "$existing_cmd" == *"uvicorn src.main:app"* || "$existing_cmd" == *"python -m uvicorn"* ]]; then
      echo "Stopping AIP server on port $PORT (PID $existing_pid)..."
      kill "$existing_pid"
      for attempt in {1..10}; do
        if ! kill -0 "$existing_pid" 2>/dev/null; then
          break
        fi
        sleep 1
      done
      if kill -0 "$existing_pid" 2>/dev/null; then
        echo "AIP server did not stop gracefully; force stopping PID $existing_pid..."
        kill -9 "$existing_pid"
      fi
      echo "Application server stopped successfully."
    fi
  done
else
  echo "No active AIP application server found running on port $PORT."
fi

# 2. Stop and spin down Docker compose containers
echo ""
echo "===== STOPPING DOCKER INFRASTRUCTURE ====="
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  if [ -d "$INFRA_DIR" ]; then
    echo "Spinning down Docker services..."
    (cd "$INFRA_DIR" && docker compose down)
    echo "Docker containers stopped and removed successfully."
  else
    echo "Infrastructure directory not found: $INFRA_DIR" >&2
  fi
else
  echo "Docker is not running or not installed. Bypassing container shutdown."
fi

echo ""
echo "==================================="
echo "AIP PLATFORM SHUT DOWN SUCCESSFULLY"
echo "==================================="
