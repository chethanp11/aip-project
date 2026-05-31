#!/usr/bin/env bash
if [ -z "${BASH_VERSION:-}" ]; then
  exec /usr/bin/env bash "$0" "$@"
fi
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_ROOT="$PROJECT_ROOT/Infra"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$PROJECT_ROOT" || exit 1

# Load environment variables if they exist in the secrets directory
if [ -f "$INFRA_ROOT/secrets/.env" ]; then
  # Export non-comment lines
  export $(grep -v '^#' "$INFRA_ROOT/secrets/.env" | xargs)
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

which "$PYTHON_BIN"

"$PYTHON_BIN" --version

which pip3 || which pip || true

echo ""
echo "===== PYTHON PACKAGES ====="

"$PYTHON_BIN" -c "
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
-U "${AIP_POSTGRES_USER:-aip}" \
-d "${AIP_POSTGRES_DB:-aipdb}" \
-c "\dx" \
| grep vector

echo ""
echo "===== NEO4J ====="

docker exec aip-neo4j \
cypher-shell \
-u "${NEO4J_USER:-neo4j}" \
-p "${NEO4J_PASSWORD:-password123}" \
"RETURN 'CONNECTED';"

echo ""
echo "===== INFRA CONNECTIVITY ====="

cd "$PROJECT_ROOT"

"$PYTHON_BIN" - << 'EOF'
import os
import sys
import psycopg2

# Ensure workspace root and src/ are in python path
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from src.shared.config import config
from src.shared.infra_client.postgres_client import PostgresClient
from src.shared.infra_client.redis_client import RedisClient
from src.shared.infra_client.neo4j_client import Neo4jClient

print("POSTGRES")
pg = PostgresClient()
conn = pg.get_connection()
print("CONNECTED")
conn.close()

print("REDIS")
r = RedisClient()
print(r.ping())

print("NEO4J")
n4j = Neo4jClient()
n4j.verify_connectivity()
print("CONNECTED")
n4j.close()

print("BUSINESS DB")
conn = psycopg2.connect(
    host=config.POSTGRES_HOST,
    database=config.POSTGRES_DB,
    user=config.POSTGRES_USER,
    password=config.POSTGRES_PASSWORD,
    port=config.POSTGRES_PORT
)
print("CONNECTED")
conn.close()
EOF

echo ""
echo "===== STORAGE ====="

cd "$INFRA_ROOT"

du -sh postgres neo4j redis

tree storage -L 2


echo ""
echo "==================================="
echo "AIP READY"
echo "==================================="