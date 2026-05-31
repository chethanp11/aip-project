"""
Neo4j Graph Database Lineage exploration tools for AIP sub-agents.
"""

from typing import Dict, Any, List

try:
    from src.shared.infra_client.neo4j_client import Neo4jClient
except ImportError:
    from shared.infra_client.neo4j_client import Neo4jClient


def retrieve_graph_lineage(metric_id: str) -> Dict[str, Any]:
    """Retrieves upstream and downstream lineage connections for a metric node from Neo4j.

    Args:
        metric_id: The ID of the target metric to retrieve lineage for (e.g. 'npl_rate').

    Returns:
        A dictionary containing list of connection records and/or status flags.
    """
    try:
        client = Neo4jClient()
        # Verify connectivity first to prevent blocking in non-graph environments
        client.verify_connectivity()
        
        # Generic lineage query: find neighbors up to 2 steps away
        query = """
        MATCH (target {id: $metric_id})-[r]-(neighbor)
        RETURN labels(target) as target_labels,
               type(r) as relationship,
               labels(neighbor) as neighbor_labels,
               neighbor.id as neighbor_id,
               neighbor.name as neighbor_name
        LIMIT 25
        """
        records = client.execute_query(query, {'metric_id': metric_id})
        
        return {
            'metric_id': metric_id,
            'lineage_found': len(records) > 0,
            'connections': records
        }
    except Exception as exc:
        print(f"[Shared Tools - Graph] Neo4j lineage check bypassed or failed: {str(exc)}")
        # Safe fallback: return empty trace without failing the workflow
        return {
            'metric_id': metric_id,
            'lineage_found': False,
            'connections': [],
            'error': str(exc)
        }
