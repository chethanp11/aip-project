"""
PostgreSQL Reusable Infrastructure Client (SQLite Migrated Version)
Natively connects to the local SQLite central database in Infra/kms/aipdb.db.
"""

import os
import sqlite3
from src.shared.config import config

class PostgresClient:
    def __init__(self):
        self.db_path = os.path.join(config.KMS_ROOT, "aipdb.db")

    def get_connection(self):
        """Establishes and returns a raw connection to the local SQLite central database."""
        # Ensure aipdb.db exists or can be created
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def execute_query(self, query: str, params: tuple = (), fetch: bool = True):
        """
        Executes a query against the local SQLite database.
        Uses dict representation to match standard RealDictCursor behavior.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Map PostgreSQL positional bindings back to SQLite bindings if any
            query_sqlite = query.replace('%s', '?')
            cursor.execute(query_sqlite, params)
            if fetch:
                results = [dict(row) for row in cursor.fetchall()]
            else:
                conn.commit()
                results = None
            return results
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def execute_many(self, query: str, params_list: list):
        """Executes a batch query (such as batch inserts) against the database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            query_sqlite = query.replace('%s', '?')
            cursor.executemany(query_sqlite, params_list)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
