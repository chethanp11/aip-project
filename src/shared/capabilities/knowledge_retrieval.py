"""
Knowledge Retrieval Capability (SQLite Vector & Graph RAG Patched)
"""

from src.shared.infra_client.retrieval_client import RetrievalClient
from typing import Dict, Any

config = {
    'description': 'Searches and compiles semantic regulations from the externalized PostgreSQL pgvector and Neo4j Graph databases.',
    'inputSchema': {
        'question': 'string'
    },
    'outputSchema': {
        'context': 'string',
        'matchesCount': 'number'
    }
}

_retrieval_client = RetrievalClient()

def handler(input_params: Dict[str, Any]) -> Dict[str, Any]:
    query = (input_params.get('question', '') or '').strip()
    if not query:
        return {
            'context': "No query provided. Retrieval requires Infra-backed KMS content.",
            'matchesCount': 0
        }
        
    try:
        # Trigger standard vector & graph RAG search through the Retrieval Service Client!
        res = _retrieval_client.search(query)
        return {
            'context': res['context'],
            'matchesCount': len(res['matched_chunks'])
        }
    except Exception as e:
        print(f"[Knowledge Retrieval Capability] RAG search error: {str(e)}")
        return {
            'context': f"Offline fallback. Grounding error: {str(e)}",
            'matchesCount': 0
        }
