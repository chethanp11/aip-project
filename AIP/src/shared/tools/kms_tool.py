"""
Generic KMS retrieval tool for AIP sub-agents.
"""

from typing import Dict, Any

from shared.intelligence import invoke_capability


async def retrieve_kms_knowledge(question: str) -> Dict[str, Any]:
    """Retrieves business glossary terms, metric definitions, and analytical templates from the KMS (Knowledge Management System).

    Args:
        question: The natural language search term or question to find relevant definitions for.
        
    Returns:
        A dictionary containing the KMS search result with 'context' and matches.
    """
    try:
        result = await invoke_capability('knowledge_retrieval', {'question': question})
        return result if isinstance(result, dict) else {}
    except Exception as exc:
        print(f"[Shared Tools - KMS] Capability 'knowledge_retrieval' failed: {str(exc)}")
        return {}
