"""
Analyst Action: Research

Provides a focused research workflow for discovering business context,
enterprise knowledge, historical artifacts, and organizational intelligence.
"""

from typing import Any, Dict

try:
    from shared.intelligence import invoke_capability
except ModuleNotFoundError:  # Support direct package imports in tests.
    from src.shared.intelligence import invoke_capability


async def run_research_workflow(query: str) -> Dict[str, Any]:
    """Run a deterministic analyst research lookup against governed knowledge."""
    normalized_query = (query or "").strip()
    if not normalized_query:
        return {
            "query": "",
            "summary": "Enter a business question, metric, data element, or artifact topic to research.",
            "matchesCount": 0,
            "sources": [],
        }

    result = await invoke_capability("knowledge_retrieval", {"question": normalized_query})
    context = result.get("context") or "No governed context was found for this research query."
    matches_count = int(result.get("matchesCount") or 0)

    return {
        "query": normalized_query,
        "summary": context,
        "matchesCount": matches_count,
        "sources": [
            "KMS canonical knowledge",
            "Historical reports",
            "Business glossary",
            "Metadata and artifact repositories",
        ],
    }
