"""
Unit and Agentic Workflow tests for Conversational BI Assistant.
"""

import os
import sys
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Ensure AIP/ and src/ are in path
aip_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../AIP"))
sys.path.insert(0, aip_root)
sys.path.insert(0, os.path.join(aip_root, "src"))

from src.reporting.conversational_bi.main import (
    run_conversational_bi_workflow,
    _repair_sql_query,
    _plan_visualizations,
    _run_quality_control
)


@patch("src.reporting.conversational_bi.main.call_llm")
@patch("src.reporting.conversational_bi.main._safe_invoke_capability")
@patch("src.reporting.conversational_bi.main.run_custom_query")
@patch("src.reporting.conversational_bi.main._schema_catalog")
def test_conv_bi_successful_flow(
    mock_schema, mock_run_query, mock_invoke_cap, mock_call_llm
):
    """Verifies the standard successful Conversational BI agent flow."""
    # 1. Mock schema catalog
    mock_schema.return_value = {
        'accounts': [{'column_name': 'branch'}, {'column_name': 'balance'}]
    }

    # 2. Mock KMS context retrieval
    mock_invoke_cap.return_value = {
        'context': ['Table accounts contains branch balances.']
    }

    # 3. Mock query planner LLM plan and narrative LLM calls
    mock_call_llm.side_effect = [
        # Query Planner JSON
        '{"queries": [{"label": "branch balances", "sql": "SELECT branch, SUM(balance) FROM accounts GROUP BY branch"}]}',
        # Narrative Writer output
        "All values are grounded. The total branch balance is $10M.",
        # Quality Control Agent response (passed)
        '{"passed": true, "violations": [], "revision_instruction": null}',
        # Visualization Planner decision
        '{"has_visual": true, "visuals": [{"type": "bar", "title": "Branch Balance", "description": "Branch distribution", "data_key": "branch balances", "config": {"label_column": "branch", "value_column": "balance", "color_scheme": "emerald"}}]}'
    ]

    # 4. Mock SQL execution outputs
    mock_run_query.return_value = [
        {'branch': 'Downtown', 'balance': 10000000.0}
    ]

    # Run workflow inside event loop
    res = asyncio.run(run_conversational_bi_workflow("What is our balance by branch?"))

    # Assert responses and keys are fully populated
    assert "narrative" in res
    assert "renderedHtml" in res
    assert "visualDecision" in res
    assert "visualHtml" in res
    assert res["visualDecision"]["has_visual"] is True
    assert "Downtown" in res["renderedHtml"]
    
    # The emerald theme maps to hex border '#10b981'
    assert "#10b981" in res["renderedHtml"]


@patch("src.reporting.conversational_bi.main.call_llm")
@patch("src.reporting.conversational_bi.main._safe_invoke_capability")
@patch("src.reporting.conversational_bi.main.run_custom_query")
@patch("src.reporting.conversational_bi.main._schema_catalog")
def test_conv_bi_sql_self_healing_loop(
    mock_schema, mock_run_query, mock_invoke_cap, mock_call_llm
):
    """Verifies that failing SQL statements are successfully caught and repaired by the SQL Debugger agent."""
    mock_schema.return_value = {
        'accounts': [{'column_name': 'branch'}, {'column_name': 'balance'}]
    }
    mock_invoke_cap.return_value = {'context': []}

    # Mock custom query: fail the first execution, succeed on second. Third is trend visualizer
    mock_run_query.side_effect = [
        # First query execution: fail due to invalid column
        Exception("column 'invalid_col' does not exist"),
        # Re-execution after repair: succeeds
        [{'branch': 'Downtown', 'balance': 500000.0}],
        # Trend visualizer query
        [{'month': '2026-05', 'total': 1500000.0}]
    ]

    mock_call_llm.side_effect = [
        # 1. Query Planner output
        '{"queries": [{"label": "invalid query", "sql": "SELECT invalid_col FROM accounts"}]}',
        # 2. SQL Debugger repair agent output
        '{"repaired_sql": "SELECT branch, balance FROM accounts"}',
        # 3. Narrative Writer output
        "Downtown has a balance of $500K.",
        # 4. QC Agent
        '{"passed": true, "violations": []}',
        # 5. Viz Planner
        '{"has_visual": false, "visuals": []}'
    ]

    res = asyncio.run(run_conversational_bi_workflow("Get accounts details"))

    # Verify repair triggered and succeeded
    assert res["narrative"] == "Downtown has a balance of $500K."
    
    # 3 total queries executed: 1 failing query, 1 repaired retry query, and 1 trend visualizer query
    assert mock_run_query.call_count == 3


@patch("src.reporting.conversational_bi.main.call_llm")
@patch("src.reporting.conversational_bi.main._safe_invoke_capability")
@patch("src.reporting.conversational_bi.main.run_custom_query")
@patch("src.reporting.conversational_bi.main._schema_catalog")
def test_conv_bi_qc_grounding_revision_loop(
    mock_schema, mock_run_query, mock_invoke_cap, mock_call_llm
):
    """Verifies that the QC agent detects ungrounded narrative hallucinations and triggers the revision loop."""
    mock_schema.return_value = {'accounts': []}
    mock_invoke_cap.return_value = {'context': []}
    mock_run_query.return_value = [{'branch': 'Uptown', 'balance': 250000.0}]

    mock_call_llm.side_effect = [
        # 1. Query Planner output
        '{"queries": [{"label": "uptown query", "sql": "SELECT * FROM accounts"}]}',
        # 2. Narrative draft (contains hallucinated 100 million value)
        "Uptown balance is $100M.",
        # 3. QC Audit 1: Fails due to numeric mismatch
        '{"passed": false, "violations": ["Ungrounded balance $100M cited, actual is $250K."], "revision_instruction": "Correct the balance to $250K."}',
        # 4. Narrative Revision output
        "Uptown balance is $250K.",
        # 5. QC Audit 2: Passes
        '{"passed": true, "violations": []}',
        # 6. Viz Planner
        '{"has_visual": false, "visuals": []}'
    ]

    res = asyncio.run(run_conversational_bi_workflow("Verify Uptown branch"))

    # Verify that the final narrative is the revised grounded draft
    assert "250K" in res["narrative"]
    assert "100M" not in res["narrative"]
