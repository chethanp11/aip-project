"""
Neo4j Reusable Infrastructure Client
Integrates natively with the externalized Neo4j Graph Database.
"""

from neo4j import GraphDatabase
from src.shared.config import config

class Neo4jClient:
    def __init__(self):
        self.uri = config.NEO4J_URI
        self.user = config.NEO4J_USER
        self.password = config.NEO4J_PASSWORD
        self._driver = None

    def get_driver(self):
        """Initializes and returns the singleton GraphDatabase driver."""
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
        return self._driver

    def verify_connectivity(self):
        """Verifies that the driver can connect to the Neo4j instance."""
        driver = self.get_driver()
        driver.verify_connectivity()

    def execute_query(self, query: str, parameters: dict = None):
        """
        Executes a Cypher query on the Neo4j database and returns list of record dicts.
        """
        driver = self.get_driver()
        with driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def close(self):
        """Closes the active connection driver."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
