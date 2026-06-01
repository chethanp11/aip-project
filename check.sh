#!/usr/bin/env bash
if [ -z "${BASH_VERSION:-}" ]; then
  exec /usr/bin/env bash "$0" "$@"
fi
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_ROOT="$PROJECT_ROOT/Infra"

cd "$PROJECT_ROOT" || exit 1

if [ -z "${VIRTUAL_ENV:-}" ]; then
  echo ""
  echo "Activating .venv..."
  if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
  fi
fi

echo ""
echo "==================================="
echo "AIP PLATFORM DIAGNOSTICS & HEALTH CHECK"
echo "==================================="

echo ""
echo "===== LOCATION ====="
pwd

echo ""
echo "===== PYTHON & PIP ====="
which python3 || true
python3 --version
which pip || true

echo ""
echo "===== VERIFYING DEPENDENCIES ====="
python3 -c "
import sqlite3
import uvicorn
import fastapi
import pydantic
import openai
import langgraph
print('CORE PYTHON LIBRARIES: OK')
"

# Optional FAISS check
python3 -c "
try:
    import faiss
    import numpy as np
    print('FAISS SEMANTIC VECTOR SEARCH: AVAILABLE')
except ImportError:
    print('FAISS SEMANTIC VECTOR SEARCH: OPTIONAL (Token Heuristics Fallback Active)')
"

echo ""
echo "===== VERIFYING PORTABLE SQLITE DATABASES ====="
python3 - << 'EOF'
import os
import sys
import sqlite3

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from src.shared.config import config

# 1. Central database check
aipdb_file = os.path.join(config.KMS_ROOT, "aipdb.db")
if not os.path.exists(aipdb_file):
    print(f"ERROR: Central database {aipdb_file} does not exist!")
    sys.exit(1)

conn = sqlite3.connect(aipdb_file)
cursor = conn.cursor()
try:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Central Database OK: Found {len(tables)} tables in aipdb.db")
    if 'kms_users' not in tables:
        print("ERROR: kms_users table missing!")
        sys.exit(1)
finally:
    conn.close()

# 2. Business analytics databases checks
business_dbs = ["treasurydb", "compliancedb", "wealthdb", "creditdb"]
for db in business_dbs:
    db_file = os.path.join(config.INFRA_ROOT, "analytics-data", f"{db}.db")
    if not os.path.exists(db_file):
        print(f"WARNING: Business database {db_file} not found!")
        continue
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall() if not row[0].startswith('sqlite_')]
        print(f"Business Database '{db}' OK: Found {len(tables)} tables")
    finally:
        conn.close()
EOF

echo ""
echo "===== EMULATION LAYERS INTEGRITY ====="
python3 - << 'EOF'
import sys
import os
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

try:
    from src.shared.infra_client.sqlite_client import SQLiteClient
    from src.shared.infra_client.graphdb_client import GraphDBClient
    from src.shared.infra_client.analytics_client import AnalyticsClient
    
    # Test SQLiteClient
    sqlite = SQLiteClient()
    conn = sqlite.get_connection()
    conn.close()
    print("SQLiteClient (KMS Storage Engine): CONNECTED")
    
    # Test GraphDBClient
    graphdb = GraphDBClient()
    graphdb.verify_connectivity()
    graphdb.execute_query("MATCH (n) RETURN n LIMIT 1;")
    print("GraphDBClient (GRAPHDB Emulation): CONNECTED")
    
    # Test AnalyticsClient
    ac = AnalyticsClient()
    tables = ac.list_tables()
    print(f"AnalyticsClient (SQLite Business Data): CONNECTED (Visible Tables: {tables})")
except Exception as e:
    print(f"INTEGRITY EXCEPTION: {e}")
    sys.exit(1)
EOF

echo ""
echo "===== PHYSICAL STORAGE STRUCTURE ====="
cd "$INFRA_ROOT"
if [ -d storage ]; then
  du -sh storage/* || true
else
  echo "storage/ directory missing!"
fi

echo ""
echo "==================================="
echo "AIP SYSTEM IS HEALTHY & PORTABLE (Zero-Docker Mode)"
echo "==================================="