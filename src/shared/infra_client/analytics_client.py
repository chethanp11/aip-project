"""
Analytics Source Database Client
Connects to business-owned PostgreSQL databases on analytics-source-db (port 5433).
Provides secure schema exploration, parameterized queries, and read-only SQL execution.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from src.shared.config import config
import re

class AnalyticsClient:
    def __init__(self):
        self.host = config.POSTGRES_HOST
        self.port = config.POSTGRES_PORT
        self.database = config.POSTGRES_DB
        self.user = config.POSTGRES_USER
        self.password = config.POSTGRES_PASSWORD

    def get_connection(self):
        """Establishes and returns a raw connection to the team's external PostgreSQL database."""
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

        # Ensure team database exists and is synchronized from the source database
        self.ensure_database_exists(db_name, team)

        return psycopg2.connect(
            host=self.host,
            port=self.port,
            database=db_name,
            user=self.user,
            password=self.password
        )

    def database_for_team(self, team: str) -> str:
        mapping = {
            'Treasury': 'treasurydb',
            'Compliance': 'compliancedb',
            'Wealth': 'wealthdb',
            'Credit': 'creditdb',
        }
        return mapping.get(team, self.database)

    def ensure_database_exists(self, db_name: str, team: str):
        """Ensures that the workspace-specific database exists, creating it if necessary."""
        if db_name == self.database:
            return

        # Connect to the base Treasury database first to check and create business databases
        conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password
        )
        conn.autocommit = True
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}';")
            exists = cursor.fetchone()
            if not exists:
                print(f"[Analytics DB] Creating team database '{db_name}'...")
                cursor.execute(f"CREATE DATABASE {db_name};")
                self.initialize_team_database(db_name, team)
        except Exception as e:
            print(f"[Analytics DB] Error ensuring database '{db_name}': {e}")
        finally:
            cursor.close()
            conn.close()

    def initialize_team_database(self, db_name: str, team: str):
        """Initializes only workspace-authorized tables in the new team database by copying from the source database."""
        team_tables_map = {
            'Treasury': ['accounts', 'transactions', 'liquidity_buffers', 'liquidity_sweeps', 'sweep_executions'],
            'Compliance': ['corporate_clients', 'transactions'],
            'Wealth': ['accounts', 'corporate_clients', 'transactions'],
            'Credit': ['corporate_clients', 'accounts', 'transactions'],
        }
        tables_to_create = team_tables_map.get(team, [])

        src_conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password
        )
        src_cursor = src_conn.cursor()

        tgt_conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            database=db_name,
            user=self.user,
            password=self.password
        )
        tgt_conn.autocommit = True
        tgt_cursor = tgt_conn.cursor()

        try:
            for t in tables_to_create:
                src_table = 'accounts' if t in ('deposits', 'loans', 'branch_performance') else t
                src_cursor.execute(f"""
                    SELECT column_name, data_type, character_maximum_length, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = '{src_table}' AND table_schema = 'public'
                    ORDER BY ordinal_position;
                """)
                cols = src_cursor.fetchall()
                if not cols:
                    continue

                col_defs = []
                for col in cols:
                    cname, dtype, clen, null_status = col
                    null_str = "NULL" if null_status == "YES" else "NOT NULL"
                    if dtype in ("character varying", "varchar"):
                        dtype_str = f"VARCHAR({clen or 255})"
                    else:
                        dtype_str = dtype
                    col_defs.append(f"{cname} {dtype_str} {null_str}")

                create_sql = f"CREATE TABLE IF NOT EXISTS {t} ({', '.join(col_defs)});"
                tgt_cursor.execute(create_sql)

                src_cursor.execute(f"SELECT * FROM {src_table};")
                rows = src_cursor.fetchall()
                if rows:
                    placeholders = ", ".join(["%s"] * len(rows[0]))
                    insert_sql = f"INSERT INTO {t} VALUES ({placeholders});"
                    tgt_cursor.executemany(insert_sql, rows)

            print(f"[Analytics DB] Successfully initialized database '{db_name}' for team '{team}'.")
        except Exception as e:
            print(f"[Analytics DB] Error initializing database '{db_name}': {e}")
        finally:
            src_cursor.close()
            src_conn.close()
            tgt_cursor.close()
            tgt_conn.close()

    def list_tables(self) -> list:
        """Returns a list of all user table names in the public schema."""
        query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query)
            tables = [row[0] for row in cursor.fetchall()]
            # Filter out internal/system tables if any
            tables = [t for t in tables if not t.startswith('pg_')]

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
        # Sanitize table name against list of existing tables
        existing_tables = self.list_tables()
        if table_name not in existing_tables:
            raise ValueError(f"Table '{table_name}' does not exist or is invalid.")

        query = """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position;
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute(query, (table_name,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[Analytics DB] Failed to fetch schema for '{table_name}': {str(e)}")
            return []
        finally:
            cursor.close()
            conn.close()

    def query_table(self, table_name: str, filters: list, limit: int = 100) -> list:
        """
        Queries a table using parameterized filters to prevent SQL injection.
        Each filter in filters list: {'column': str, 'operator': str, 'value': Any}
        """
        # 1. Sanitize Table Name
        existing_tables = self.list_tables()
        if table_name not in existing_tables:
            raise ValueError(f"Invalid table name: {table_name}")

        # 2. Get valid columns for sanitization
        schema = self.get_table_schema(table_name)
        valid_columns = {col['column_name'] for col in schema}

        query_str = f"SELECT * FROM {table_name}"
        where_clauses = []
        params = []

        # 3. Build parameterized WHERE clause safely
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
                where_clauses.append(f"{col} IS NULL")
            elif op == 'IS NOT NULL':
                where_clauses.append(f"{col} IS NOT NULL")
            elif op == 'LIKE':
                where_clauses.append(f"{col} LIKE %s")
                # Automatically add wildcards if not already present
                val_str = str(val)
                if '%' not in val_str:
                    val_str = f"%{val_str}%"
                params.append(val_str)
            else:
                where_clauses.append(f"{col} {op} %s")
                params.append(val)

        if where_clauses:
            query_str += " WHERE " + " AND ".join(where_clauses)

        # Add safe sorting and limit
        query_str += f" LIMIT {int(limit)};"

        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
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
        """
        Executes a custom read-only SQL query against the source database.
        Enforces strict read-only keyword verification to block write operations.
        """
        cleaned = sql_query.strip()
        # 1. Enforce SELECT or WITH prefix
        if not re.match(r'^\s*(SELECT|WITH)\b', cleaned, re.IGNORECASE):
            raise PermissionError("Only read-only queries starting with 'SELECT' or 'WITH' are permitted.")

        # 2. Block write command keywords
        forbidden = r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|REPLACE|RENAME|COMMIT|ROLLBACK|BEGIN)\b'
        if re.search(forbidden, cleaned, re.IGNORECASE):
            raise PermissionError("Security Violation: DDL and DML write operations are strictly blocked.")

        # 3. Dynamic context-data filtering checking referenced tables
        from shared.intelligence import active_agent_context
        from shared.session import active_sessions
        active_ctx = active_agent_context.get()
        api_key = active_ctx.get('api_key', '') if active_ctx else ''
        allowed_tables = None
        if api_key in active_sessions:
            allowed_tables = active_sessions[api_key].get('allowed_tables')

        if allowed_tables is not None:
            # Tokenize SQL query to find table references
            sql_words = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', cleaned.lower()))

            # Fetch master un-filtered list of public tables supporting both PostgreSQL and SQLite
            master_tables = []
            conn = self.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
                master_tables = [list(row.values())[0].lower() if isinstance(row, dict) else row[0].lower() for row in cursor.fetchall() if not (list(row.values())[0] if isinstance(row, dict) else row[0]).startswith('pg_')]
            except Exception:
                try:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    master_tables = [list(row.values())[0].lower() if isinstance(row, dict) else row[0].lower() for row in cursor.fetchall() if not (list(row.values())[0] if isinstance(row, dict) else row[0]).startswith('sqlite_')]
                except Exception:
                    pass
            finally:
                cursor.close()
                conn.close()

            for t in master_tables:
                if t in sql_words and t not in allowed_tables:
                    raise PermissionError(f"Access Denied: You do not have permission to query database table '{t}' under your active user profile.")

        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute(sql_query)
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[Analytics DB] Custom SQL failed: {str(e)}")
            raise e
        finally:
            cursor.close()
            conn.close()

    def get_table_rows(self, table_name: str, limit: int = 1000) -> list:
        """Return rows from an authorized analytics table without file-based bootstrap access."""
        return self.query_table(table_name, [], limit)

    def run_compatible_read_query(self, sql: str, params: tuple = ()) -> list:
        """Run read-only SQL while accepting legacy '?' placeholders."""
        sql_pg = sql.replace("?", "%s")
        cleaned = sql_pg.strip()
        if not re.match(r'^\s*(SELECT|WITH)\b', cleaned, re.IGNORECASE):
            raise PermissionError("Only read-only queries starting with 'SELECT' or 'WITH' are permitted.")

        forbidden = r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|REPLACE|RENAME|COMMIT|ROLLBACK|BEGIN)\b'
        if re.search(forbidden, cleaned, re.IGNORECASE):
            raise PermissionError("Security Violation: DDL and DML write operations are strictly blocked.")

        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute(sql_pg, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()
