import asyncio

from src.analyst_actions.research.main import run_research_workflow


def test_research_workflow_empty_query_is_deterministic():
    result = asyncio.run(run_research_workflow("   "))

    assert result["query"] == ""
    assert result["matchesCount"] == 0
    assert "Enter a business question" in result["summary"]
    assert result["sources"] == []
