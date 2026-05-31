#!/usr/bin/env bash
if [ -z "${BASH_VERSION:-}" ]; then
  exec /usr/bin/env bash "$0" "$@"
fi
set -euo pipefail
AIP_SKIP_INFRA="${AIP_SKIP_INFRA:-1}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$REPO_ROOT"
INFRA_DIR="$REPO_ROOT/Infra/docker"

if [ ! -d "$APP_DIR" ]; then
  echo "AIP application directory not found: $APP_DIR" >&2
  exit 1
fi

cd "$REPO_ROOT"

# Load environment variables if they exist in the secrets directory
if [ -f "$REPO_ROOT/Infra/secrets/.env" ]; then
  # Export non-comment lines
  export $(grep -v '^#' "$REPO_ROOT/Infra/secrets/.env" | xargs)
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python executable not found: $PYTHON_BIN" >&2
  echo "Install Python 3, or run with: PYTHON_BIN=/path/to/python ./start.sh" >&2
  exit 1
fi

echo "Using Python: $($PYTHON_BIN --version)"
if "$PYTHON_BIN" -c "import fastapi, uvicorn, pydantic" >/dev/null 2>&1; then
  echo "Python dependencies already available."
else
  echo "Preparing Python dependencies..."
  PIP_FLAGS=""
  # Add --break-system-packages if not in a venv and PEP 668 is active or flag is supported
  if [ -z "${VIRTUAL_ENV:-}" ]; then
    PIP_FLAGS="--break-system-packages"
  fi
  "$PYTHON_BIN" -m pip install $PIP_FLAGS --upgrade pip setuptools wheel
  cd "$APP_DIR"
  "$PYTHON_BIN" -m pip install $PIP_FLAGS --prefer-binary -r "$REPO_ROOT/requirements.txt"
  cd "$REPO_ROOT"
fi

if [ "${AIP_SKIP_INFRA:-}" != "1" ]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is not installed or not on PATH." >&2
    echo "Install/start Docker Desktop, then rerun: sh start.sh" >&2
    exit 1
  fi

  if ! docker info >/dev/null 2>&1; then
    echo "Docker daemon is not running or is not reachable." >&2
    echo "Start Docker Desktop, wait until it is ready, then rerun: sh start.sh" >&2
    exit 1
  fi

  if [ ! -d "$INFRA_DIR" ]; then
    echo "AIP infrastructure directory not found: $INFRA_DIR" >&2
    exit 1
  fi

  echo "Starting AIP infrastructure..."
  (cd "$INFRA_DIR" && docker compose up -d)

  echo "Waiting for analytics PostgreSQL..."
  for attempt in {1..30}; do
    if docker exec analytics-source-db pg_isready -U "${POSTGRES_USER:-analytics}" -d "${POSTGRES_DB:-analyticsdb}" >/dev/null 2>&1; then
      break
    fi
    if [ "$attempt" -eq 30 ]; then
      echo "analytics-source-db did not become ready in time." >&2
      exit 1
    fi
    sleep 1
  done
fi

cd "$APP_DIR"

existing_pids="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"
if [ -n "$existing_pids" ]; then
  for existing_pid in $existing_pids; do
    existing_cmd="$(ps -p "$existing_pid" -o command= 2>/dev/null || true)"
    if [[ "$existing_cmd" == *"uvicorn src.main:app"* ]]; then
      echo "Stopping existing AIP server on port $PORT (PID $existing_pid)..."
      kill "$existing_pid"
      for attempt in {1..10}; do
        if ! kill -0 "$existing_pid" 2>/dev/null; then
          break
        fi
        sleep 1
      done
      if kill -0 "$existing_pid" 2>/dev/null; then
        echo "Existing AIP server did not stop; force stopping PID $existing_pid..."
        kill -9 "$existing_pid"
      fi
    else
      echo "Port $PORT is already in use by PID $existing_pid:" >&2
      echo "$existing_cmd" >&2
      echo "Stop that process or run with a different port: PORT=8001 sh start.sh" >&2
      exit 1
    fi
  done
fi

echo "Starting AIP at http://$HOST:$PORT"
if [ "${AIP_DEV_RELOAD:-}" = "1" ]; then
  exec "$PYTHON_BIN" -m uvicorn src.main:app --host "$HOST" --port "$PORT" --reload
fi

exec "$PYTHON_BIN" -m uvicorn src.main:app --host "$HOST" --port "$PORT"
