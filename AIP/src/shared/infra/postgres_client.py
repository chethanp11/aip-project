"""
PostgreSQL Reusable Infrastructure Client
Integrates natively with the externalized pgvector container.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from src.shared.config import config

class PostgresClient:
    def __init__(self):
        self.host = config.AIP_POSTGRES_HOST
        self.port = config.AIP_POSTGRES_PORT
        self.database = config.AIP_POSTGRES_DB
        self.user = config.AIP_POSTGRES_USER
        self.password = config.AIP_POSTGRES_PASSWORD

    def get_connection(self):
        """Establishes and returns a raw connection to the external PostgreSQL database."""
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password
        )

    def execute_query(self, query: str, params: tuple = (), fetch: bool = True):
        """
        Executes a query against the PostgreSQL database.
        Uses RealDictCursor to match the standard SQLite Row factory behavior (accessing fields as dict keys).
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            # PostgreSQL uses %s instead of ? for parameter binding
            query_pg = query.replace('?', '%s')
            cursor.execute(query_pg, params)
            if fetch:
                results = cursor.fetchall()
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
            query_pg = query.replace('?', '%s')
            cursor.executemany(query_pg, params_list)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
