"""
Analytics Source Database Client (SQLite Migrated Version)
Connects directly to portable local SQLite databases under Infra/analytics-data/.
Provides secure schema exploration, parameterized queries, and read-only SQL execution.
"""

import os
import sqlite3
import re
from src.shared.config import config

class AnalyticsClient:
    def __init__(self):
        self.database = config.POSTGRES_DB  # default is treasurydb
        self.data_dir = os.path.join(config.INFRA_ROOT, "analytics-data")

    def get_connection(self):
        """Establishes and returns a raw connection to the team's local SQLite database."""
        # Resolve team based on active user profile
        from shared.intelligence import active_agent_context
        from shared.session import active_sessions
        from src.shared.config import config

        active_ctx = active_agent_context.get()
        api_key = active_ctx.get('api_key', '') if active_ctx else ''
        username = None
        allowed_domains = None
        if api_key in active_sessions:
            username = active_sessions[api_key].get('username')
            allowed_domains = active_sessions[api_key].get('allowed_domains')

        team = config.resolve_kms_team(username, allowed_domains)
        db_name = self.database_for_team(team)

        db_file = os.path.join(self.data_dir, f"{db_name}.db")
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        return conn

    def database_for_team(self, team: str) -> str:
        mapping = {
            'Treasury': 'treasurydb',
            'Compliance': 'compliancedb',
            'Wealth': 'wealthdb',
            'Credit': 'creditdb',
        }
        return mapping.get(team, self.database)

    def ensure_database_exists(self, db_name: str, team: str):
        """No-op as databases are fully pre-populated SQLite files."""
        pass

    def list_tables(self) -> list:
        """Returns a list of all user table names in the SQLite database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            # Filter out internal/system tables and metadata tables
            tables = [t for t in tables if not (t.startswith('sqlite_') or t in ('vector_chunks', 'canonical_knowledge', 'security_audit_logs', 'governance_approvals', 'observability_metrics', 'source_connectors', 'candidate_knowledge', 'business_domains', 'business_terms', 'metrics_glossary', 'analytical_templates', 'knowledge_articles', 'kms_users', 'workflow_runs', 'workflow_node_metrics', 'ui_configurations'))]

            # Dynamic filtering based on active analyst allowed_tables
            from shared.intelligence import active_agent_context
            from shared.session import active_sessions
            active_ctx = active_agent_context.get()
            api_key = active_ctx.get('api_key', '') if active_ctx else ''
            allowed_tables = None
            if api_key in active_sessions:
                allowed_tables = active_sessions[api_key].get('allowed_tables')

            if allowed_tables is not None:
                tables = [t for t in tables if t.lower() in allowed_tables]

            return tables
        except Exception as e:
            print(f"[Analytics DB] Failed to list tables: {str(e)}")
            return []
        finally:
            cursor.close()
            conn.close()

    def get_table_schema(self, table_name: str) -> list:
        """Returns column names and data types for the specified table."""
        existing_tables = self.list_tables()
        if table_name not in existing_tables:
            raise ValueError(f"Table '{table_name}' does not exist or is invalid.")

        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # PRAGMA table_info returns columns: cid, name, type, notnull, dflt_value, pk
            cursor.execute(f'PRAGMA table_info("{table_name}");')
            return [{'column_name': row['name'], 'data_type': row['type']} for row in cursor.fetchall()]
        except Exception as e:
            print(f"[Analytics DB] Failed to fetch schema for '{table_name}': {str(e)}")
            return []
        finally:
            cursor.close()
            conn.close()

    def query_table(self, table_name: str, filters: list, limit: int = 100) -> list:
        """Queries a table using parameterized filters safely."""
        existing_tables = self.list_tables()
        if table_name not in existing_tables:
            raise ValueError(f"Invalid table name: {table_name}")

        schema = self.get_table_schema(table_name)
        valid_columns = {col['column_name'] for col in schema}

        query_str = f'SELECT * FROM "{table_name}"'
        where_clauses = []
        params = []

        operator_map = {
            'equals': '=',
            '=': '=',
            'greater_than': '>',
            '>': '>',
            'less_than': '<',
            '<': '<',
            'contains': 'LIKE',
            'like': 'LIKE',
            'is_null': 'IS NULL',
            'is_not_null': 'IS NOT NULL'
        }

        for f in filters:
            col = f.get('column')
            op_name = f.get('operator', 'equals').lower()
            val = f.get('value')

            if col not in valid_columns:
                raise ValueError(f"Invalid column: {col} for table {table_name}")

            op = operator_map.get(op_name)
            if not op:
                raise ValueError(f"Unsupported operator: {op_name}")

            if op == 'IS NULL':
                where_clauses.append(f'"{col}" IS NULL')
            elif op == 'IS NOT NULL':
                where_clauses.append(f'"{col}" IS NOT NULL')
            elif op == 'LIKE':
                where_clauses.append(f'"{col}" LIKE ?')
                val_str = str(val)
                if '%' not in val_str:
                    val_str = f"%{val_str}%"
                params.append(val_str)
            else:
                where_clauses.append(f'"{col}" {op} ?')
                params.append(val)

        if where_clauses:
            query_str += " WHERE " + " AND ".join(where_clauses)

        query_str += f" LIMIT {int(limit)};"

        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query_str, tuple(params))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[Analytics DB] Filtered query failed: {str(e)}")
            raise e
        finally:
            cursor.close()
            conn.close()

    def run_custom_query(self, sql_query: str) -> list:
        """Executes a custom read-only SQLite query against the database."""
        cleaned = sql_query.strip()
        if not re.match(r'^\s*(SELECT|WITH)\b', cleaned, re.IGNORECASE):
            raise PermissionError("Only read-only queries starting with 'SELECT' or 'WITH' are permitted.")

        forbidden = r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|REPLACE|RENAME|COMMIT|ROLLBACK|BEGIN)\b'
        if re.search(forbidden, cleaned, re.IGNORECASE):
            raise PermissionError("Security Violation: DDL and DML write operations are strictly blocked.")

        # Dynamic context-data filtering checking referenced tables
        from shared.intelligence import active_agent_context
        from shared.session import active_sessions
        active_ctx = active_agent_context.get()
        api_key = active_ctx.get('api_key', '') if active_ctx else ''
        allowed_tables = None
        if api_key in active_sessions:
            allowed_tables = active_sessions[api_key].get('allowed_tables')

        if allowed_tables is not None:
            sql_words = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', cleaned.lower()))
            master_tables = []
            conn = self.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                master_tables = [row[0].lower() for row in cursor.fetchall() if not row[0].startswith('sqlite_')]
            finally:
                cursor.close()
                conn.close()

            for t in master_tables:
                if t in sql_words and t not in allowed_tables:
                    raise PermissionError(f"Access Denied: You do not have permission to query database table '{t}' under your active user profile.")

        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Map %s back to ? in query
            sql_query_sqlite = sql_query.replace('%s', '?')
            cursor.execute(sql_query_sqlite)
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[Analytics DB] Custom SQL failed: {str(e)}")
            raise e
        finally:
            cursor.close()
            conn.close()

    def get_table_rows(self, table_name: str, limit: int = 1000) -> list:
        return self.query_table(table_name, [], limit)

    def run_compatible_read_query(self, sql: str, params: tuple = ()) -> list:
        """Run read-only SQL with compatible placeholder mappings."""
        sql_sqlite = sql.replace("%s", "?")
        cleaned = sql_sqlite.strip()
        if not re.match(r'^\s*(SELECT|WITH)\b', cleaned, re.IGNORECASE):
            raise PermissionError("Only read-only queries starting with 'SELECT' or 'WITH' are permitted.")

        forbidden = r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|REPLACE|RENAME|COMMIT|ROLLBACK|BEGIN)\b'
        if re.search(forbidden, cleaned, re.IGNORECASE):
            raise PermissionError("Security Violation: DDL and DML write operations are strictly blocked.")

        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(sql_sqlite, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()
