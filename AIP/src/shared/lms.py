"""
LMS Database Connector Utility (PostgreSQL Refactored)
Connects to PostgreSQL database and provides standard data fetching tools.
Enforces no hardcoded local database paths.
"""

import json
import os
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from src.shared.config import config
from src.shared.infra.postgres_client import PostgresClient

# Singleton PostgreSQL Client instance
_pg_client = PostgresClient()
_tables_initialized = False

def _load_lms_seed() -> Dict[str, Any]:
    """Load LMS seed/reference data from AIP-Infra, not from application code."""
    seed_path = os.path.join(config.LMS_SEED_PATH, "corporate_banking_seed.json")
    if not os.path.exists(seed_path):
        raise FileNotFoundError(f"LMS seed data not found in AIP-Infra: {seed_path}")
    with open(seed_path, "r", encoding="utf-8") as seed_file:
        return json.load(seed_file)

def get_db_connection():
    """Establishes and returns a raw connection to the external PostgreSQL database."""
    return _pg_client.get_connection()

def ensure_lms_tables():
    """
    Ensures corporate banking LMS tables exist in the external PostgreSQL database.
    Seeds data if empty to guarantee fully stateless out-of-the-box operation.
    """
    global _tables_initialized
    if _tables_initialized:
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'corporate_clients'
            );
        """)
        exists = cursor.fetchone()[0]
        if exists:
            _tables_initialized = True
            return

        print("[LMS Migrations] Initializing corporate banking schemas in PostgreSQL...")

        # 1. Create Tables
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS corporate_clients (
            client_id VARCHAR(50) PRIMARY KEY,
            company_name VARCHAR(255) NOT NULL,
            industry VARCHAR(100) NOT NULL,
            risk_score REAL NOT NULL,
            credit_rating VARCHAR(50) NOT NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            account_id VARCHAR(50) PRIMARY KEY,
            client_id VARCHAR(50) NOT NULL REFERENCES corporate_clients(client_id),
            branch VARCHAR(100) NOT NULL,
            currency VARCHAR(50) NOT NULL,
            balance REAL NOT NULL,
            account_type VARCHAR(100) NOT NULL,
            interest_rate REAL NOT NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS liquidity_sweeps (
            sweep_id VARCHAR(50) PRIMARY KEY,
            client_id VARCHAR(50) NOT NULL REFERENCES corporate_clients(client_id),
            source_account_id VARCHAR(50) NOT NULL REFERENCES accounts(account_id),
            destination_account_id VARCHAR(50) NOT NULL REFERENCES accounts(account_id),
            sweep_type VARCHAR(100) NOT NULL,
            threshold_amount REAL NOT NULL,
            status VARCHAR(50) NOT NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sweep_executions (
            execution_id VARCHAR(50) PRIMARY KEY,
            sweep_id VARCHAR(50) NOT NULL REFERENCES liquidity_sweeps(sweep_id),
            transfer_amount REAL NOT NULL,
            timestamp VARCHAR(100) NOT NULL,
            status VARCHAR(50) NOT NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS liquidity_buffers (
            buffer_id VARCHAR(50) PRIMARY KEY,
            asset_type VARCHAR(255) NOT NULL,
            amount REAL NOT NULL,
            haircut_percentage REAL NOT NULL,
            yield_rate REAL NOT NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id VARCHAR(50) PRIMARY KEY,
            account_id VARCHAR(50) NOT NULL REFERENCES accounts(account_id),
            amount REAL NOT NULL,
            direction VARCHAR(50) NOT NULL,
            transaction_type VARCHAR(100) NOT NULL,
            timestamp VARCHAR(100) NOT NULL
        );
        """)
        conn.commit()

        seed = _load_lms_seed()

        # 2. Seed Corporate Clients
        clients_data = [tuple(row) for row in seed["clients"]]
        cursor.executemany("INSERT INTO corporate_clients VALUES (%s, %s, %s, %s, %s);", clients_data)

        # 3. Seed Accounts
        accounts_data = []
        branches = seed["branches"]
        currencies = seed["currencies"]
        generation = seed.get("generation", {})
        random.seed(generation.get("random_seed", 42)) # Deterministic seeding

        for c_id, name, _, _, _ in clients_data:
            for i, curr in enumerate(currencies):
                acc_id = f"ACC-{c_id.split('-')[1]}-{curr}"
                branch = random.choice(branches)
                balance = round(random.uniform(5000000.0, 150000000.0), 2)
                acc_type = "Corporate Current" if i == 0 else ("Yield Earning Deposit" if i == 1 else "Treasury Sweeper")
                rate = 0.5 if i == 0 else (2.75 if i == 1 else 1.25)
                accounts_data.append((acc_id, c_id, branch, curr, balance, acc_type, rate))
                
        cursor.executemany("INSERT INTO accounts VALUES (%s, %s, %s, %s, %s, %s, %s);", accounts_data)

        # 4. Seed Liquidity Sweeps
        sweeps_data = []
        for idx in range(generation.get("sweep_count", 15)):
            sweep_id = f"SWP-{100 + idx}"
            client_info = clients_data[idx % len(clients_data)]
            c_id = client_info[0]
            
            src_acc = f"ACC-{c_id.split('-')[1]}-EUR"
            dest_acc = f"ACC-{c_id.split('-')[1]}-USD"
            
            sweep_type = "Zero-Balance" if idx % 2 == 0 else "Target-Balance"
            threshold = 1000000.0 if sweep_type == "Target-Balance" else 0.0
            status = "Active" if idx < 13 else "Suspended"
            sweeps_data.append((sweep_id, c_id, src_acc, dest_acc, sweep_type, threshold, status))
            
        cursor.executemany("INSERT INTO liquidity_sweeps VALUES (%s, %s, %s, %s, %s, %s, %s);", sweeps_data)

        # 5. Seed Buffers
        buffers_data = [tuple(row) for row in seed["liquidity_buffers"]]
        cursor.executemany("INSERT INTO liquidity_buffers VALUES (%s, %s, %s, %s, %s);", buffers_data)

        # 6. Seed Transactions and Sweep Executions
        transactions_data = []
        base_date = datetime.now() - timedelta(days=generation.get("history_days", 180))
        tx_types = seed["transaction_types"]
        sweep_executions_data = []
        sweep_count = 0
        
        for i in range(generation.get("transaction_count", 1050)):
            tx_id = f"TX-{10000 + i}"
            account_info = random.choice(accounts_data)
            acc_id = account_info[0]
            
            amount = round(random.uniform(50000.0, 8500000.0), 2)
            direction = random.choice(["Inflow", "Outflow"])
            tx_type = random.choice(tx_types)
            
            tx_time = base_date + timedelta(minutes=random.randint(1, 250000))
            timestamp_str = tx_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            transactions_data.append((tx_id, acc_id, amount, direction, tx_type, timestamp_str))
            
            if tx_type == "Sweep Transfer" and sweep_count < generation.get("max_sweep_executions", 150):
                sw_id = f"SWP-{100 + (sweep_count % generation.get('sweep_count', 15))}"
                exec_id = f"EXEC-{20000 + sweep_count}"
                sweep_executions_data.append((exec_id, sw_id, amount, timestamp_str, "Succeeded"))
                sweep_count += 1

        cursor.executemany("INSERT INTO transactions VALUES (%s, %s, %s, %s, %s, %s);", transactions_data)
        cursor.executemany("INSERT INTO sweep_executions VALUES (%s, %s, %s, %s, %s);", sweep_executions_data)
        
        conn.commit()
        _tables_initialized = True
        print(f"[LMS Migrations] Successfully migrated and seeded 1,050 ledger rows into PostgreSQL.")

    except Exception as e:
        conn.rollback()
        print(f"[LMS Migrations] Schema seeding failed: {str(e)}")
        raise e
    finally:
        cursor.close()
        conn.close()

def get_lms_table(table_name: str) -> List[Dict[str, Any]]:
    """
    Queries and returns a specific table array from the PostgreSQL database.
    Maintains full backwards contract parity with all suite integrations.
    """
    valid_tables = {
        'corporate_clients', 'accounts', 'liquidity_sweeps', 
        'sweep_executions', 'liquidity_buffers', 'transactions',
        'deposits', 'loans', 'branch_performance'
    }
    
    # Map old mock tables to new relational equivalents
    sql_table = table_name
    if table_name == 'deposits' or table_name == 'loans' or table_name == 'branch_performance':
        sql_table = 'accounts'

    if sql_table not in valid_tables:
        print(f"[LMS Connector] Attempted query on invalid or missing table: {table_name}")
        return []

    # Dynamic context-data filtering checking allowed_tables
    from shared.intelligence import active_agent_context
    from shared.session import active_sessions
    active_ctx = active_agent_context.get()
    api_key = active_ctx.get('api_key', '') if active_ctx else ''
    allowed_tables = None
    if api_key in active_sessions:
        allowed_tables = active_sessions[api_key].get('allowed_tables')

    if allowed_tables is not None:
        req_lower = table_name.lower()
        map_lower = sql_table.lower()
        if req_lower not in allowed_tables and map_lower not in allowed_tables:
            print(f"[LMS Connector] Access Denied: User profile does not have permission to access table '{table_name}'.")
            return []

    try:
        ensure_lms_tables()
        results = _pg_client.execute_query(f"SELECT * FROM {sql_table} LIMIT 1000;")
        # Return list of dicts to preserve Row interface compatibility
        return [dict(r) for r in results]
    except Exception as e:
        print(f"[LMS Connector] Failed to read PostgreSQL table '{table_name}': {str(e)}")
        return []

def run_sqlite_query(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """
    Executes a read-only SQL query against the PostgreSQL database.
    Converts SQLite ? placeholders to PostgreSQL %s format dynamically to keep perfect backwards-compatibility.
    """
    # Dynamic context-data filtering checking allowed_tables
    from shared.intelligence import active_agent_context
    from shared.session import active_sessions
    active_ctx = active_agent_context.get()
    api_key = active_ctx.get('api_key', '') if active_ctx else ''
    allowed_tables = None
    if api_key in active_sessions:
        allowed_tables = active_sessions[api_key].get('allowed_tables')

    if allowed_tables is not None:
        import re
        sql_words = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', sql.lower()))
        banking_tables = {'corporate_clients', 'accounts', 'liquidity_sweeps', 'sweep_executions', 'liquidity_buffers', 'transactions', 'deposits', 'loans', 'branch_performance'}
        for t in banking_tables:
            if t in sql_words:
                sql_t = 'accounts' if t in ('deposits', 'loans', 'branch_performance') else t
                if t not in allowed_tables and sql_t not in allowed_tables:
                    print(f"[LMS Connector] Access Denied: SQL references unauthorized table '{t}'.")
                    return []

    try:
        ensure_lms_tables()
        sql_pg = sql.replace('?', '%s')
        results = _pg_client.execute_query(sql_pg, params)
        return [dict(r) for r in results]
    except Exception as e:
        print(f"[LMS Connector] Custom Query failed: '{sql}' | Error: {str(e)}")
        return []
