"""
SQLite Reusable Infrastructure Client
Natively connects to the local SQLite central database in Infra/kms/aipdb.db.
"""

import os
import sqlite3
from src.shared.config import config

def left_func(s, n):
    if s is None:
        return None
    try:
        return str(s)[:int(n)]
    except Exception:
        return str(s)

def right_func(s, n):
    if s is None:
        return None
    try:
        n = int(n)
        if n <= 0:
            return ""
        return str(s)[-n:]
    except Exception:
        return str(s)

def concat_func(*args):
    return "".join(str(a) for a in args if a is not None)

class SQLiteClient:
    def __init__(self):
        self.db_path = os.path.join(config.KMS_ROOT, "aipdb.db")

    def get_connection(self):
        """Establishes and returns a raw connection to the local SQLite central database."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # Register compatibility functions
        conn.create_function("LEFT", 2, left_func)
        conn.create_function("left", 2, left_func)
        conn.create_function("RIGHT", 2, right_func)
        conn.create_function("right", 2, right_func)
        conn.create_function("CONCAT", -1, concat_func)
        conn.create_function("concat", -1, concat_func)
        
        return conn

    def execute_query(self, query: str, params: tuple = (), fetch: bool = True):
        """
        Executes a query against the local SQLite database.
        Uses dict representation to match standard Row behavior.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
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
        """Executes a batch query against the database."""
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
