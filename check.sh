#!/usr/bin/env bash
if [ -z "${BASH_VERSION:-}" ]; then
  exec /usr/bin/env bash "$0" "$@"
fi
set -euo pipefail

PROJECT_ROOT="/Users/chethan/GitHub/AIP-Project/AIP"
INFRA_ROOT="/Users/chethan/GitHub/AIP-Project/AIP-Infra"

cd "$PROJECT_ROOT" || exit 1

if [ -z "${VIRTUAL_ENV:-}" ]; then
  echo ""
  echo "Activating .venv..."
  source .venv/bin/activate
fi

echo ""
echo "==================================="
echo "AIP PLATFORM HEALTH CHECK"
echo "==================================="

echo ""
echo "===== LOCATION ====="

pwd

echo ""
echo "===== PYTHON ====="

which python

python --version

which pip

echo ""
echo "===== PYTHON PACKAGES ====="

python -c "
import psycopg2
import redis
import neo4j
import openai
import langgraph
print('CORE_PACKAGES_OK')
"

if [ $? -ne 0 ]; then
  echo "PACKAGE ISSUE"
  exit 1
fi

echo ""
echo "===== STARTING INFRA ====="

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed or not on PATH." >&2
  echo "Install/start Docker Desktop, then rerun: sh check.sh" >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not running or is not reachable." >&2
  echo "Start Docker Desktop, wait until it is ready, then rerun: sh check.sh" >&2
  exit 1
fi

cd "$INFRA_ROOT/docker" || exit 1

docker compose up -d

echo ""
echo "===== CONTAINERS ====="

docker ps \
--format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "===== POSTGRES ====="

docker exec aip-postgres pg_isready

echo ""
echo "===== REDIS ====="

docker exec aip-redis redis-cli ping

echo ""
echo "===== VECTOR ====="

docker exec -i aip-postgres \
psql \
-U aip \
-d aipdb \
-c "\dx" \
| grep vector

echo ""
echo "===== NEO4J ====="

docker exec aip-neo4j \
cypher-shell \
-u neo4j \
-p password123 \
"RETURN 'CONNECTED';"

echo ""
echo "===== INFRA CONNECTIVITY ====="

cd "$PROJECT_ROOT"

python test_infra.py

echo ""
echo "===== STORAGE ====="

cd "$INFRA_ROOT"

du -sh postgres neo4j redis

tree storage -L 2


echo ""
echo "==================================="
echo "AIP READY"
echo "==================================="