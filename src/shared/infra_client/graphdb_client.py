"""
GraphDB Reusable Infrastructure Client
Enables graph reads (lineage and node queries) directly from the local relational SQLite database
without requiring GRAPHDB to be installed or running.
"""

import os
import sqlite3
from src.shared.config import config

class GraphDBClient:
    def __init__(self):
        self.db_path = os.path.join(config.KMS_ROOT, "aipdb.db")

    def get_driver(self):
        """Returns self as a dummy driver instance."""
        return self

    def verify_connectivity(self):
        """No-op as SQLite connectivity is local and checked separately."""
        pass

    def execute_query(self, query: str, parameters: dict = None):
        """
        Emulates Cypher queries against GRAPHDB by querying SQLite graph tables directly.
        Particularly supports the target/neighbor lineage connections query.
        """
        parameters = parameters or {}
        if "target" in query and "neighbor" in query:
            metric_id = parameters.get("metric_id")
            if not metric_id:
                return []

            if not os.path.exists(self.db_path):
                return []

            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT n.node_id, n.title, n.type, e.relationship
                    FROM graph_edges e
                    JOIN graph_nodes n ON (e.target_id = n.node_id OR e.source_id = n.node_id)
                    WHERE (e.source_id = ? OR e.target_id = ?) AND n.node_id != ?
                    LIMIT 25
                """, (metric_id, metric_id, metric_id))
                
                records = []
                for row in cursor.fetchall():
                    records.append({
                        'target_labels': ['KnowledgeNode'],
                        'relationship': row['relationship'],
                        'neighbor_labels': [row['type']],
                        'neighbor_id': row['node_id'],
                        'neighbor_name': row['title']
                    })
                return records
            except Exception as e:
                print(f"[Mock GraphDB] Failed to resolve graph lineage from SQLite: {e}")
                return []
            finally:
                cursor.close()
                conn.close()
        
        return []

    def close(self):
        """No-op."""
        pass
