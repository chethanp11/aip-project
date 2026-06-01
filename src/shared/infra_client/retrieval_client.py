"""
Retrieval Reusable Infrastructure Client
Standardizes retrieval logic as a standalone Retrieval Service.
Implements the architecture rule: Agent -> Retrieval Service -> FAISS
"""

from typing import Dict, Any

class RetrievalClient:
    def __init__(self):
        # The retrieval client sits in the shared infra package
        pass

    def search(self, query: str, limit: int = 4) -> Dict[str, Any]:
        """
        Executes a search against the grounding layers (SQLite & GRAPHDB).
        This abstracts the database queries from the agent directly.
        """
        from src.kms.index import advanced_retrieval_orchestration
        # Delegate to the advanced retrieval orchestrator which runs queries on SQLite & GRAPHDB
        return advanced_retrieval_orchestration(query, "Analyst", "Internal", limit)
