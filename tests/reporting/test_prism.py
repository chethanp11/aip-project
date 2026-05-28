"""
Unit tests for the PRISM Report Rationalizer (Stateful Agentic AI)
"""

import os
import sys
import pytest

# Ensure AIP/ and src/ are in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../AIP")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../AIP/src")))

from src.reporting.prism.main import (
    run_prism_workflow,
    parse_excel_report,
    parse_html_report
)

@pytest.mark.anyio
async def test_run_prism_workflow_exact_duplicates():
    """
    Verifies that reports with the exact same SQL queries are detected as duplicates.
    """
    reports = [
        {
            'name': 'Branch Cash Flow Q1',
            'query': 'SELECT cash_inflow, cash_outflow FROM branch_ledger',
            'columns': ['cash_inflow', 'cash_outflow'],
            'usage': 50,
            'owner': 'Treasury',
            'type': 'SQL Ledger'
        },
        {
            'name': 'Cash Movements Audit',
            'query': 'SELECT cash_inflow, cash_outflow FROM branch_ledger',
            'columns': ['cash_inflow', 'cash_outflow'],
            'usage': 12,
            'owner': 'Finance',
            'type': 'SQL Ledger'
        }
    ]
    
    results = await run_prism_workflow(reports)
    
    assert len(results['duplicates']) == 1
    assert results['duplicates'][0]['reportA'] == 'Branch Cash Flow Q1'
    assert results['duplicates'][0]['reportB'] == 'Cash Movements Audit'
    assert 'Exact SQL' in results['duplicates'][0]['matchType']

@pytest.mark.anyio
async def test_run_prism_workflow_overlaps():
    """
    Verifies that reports sharing a high proportion of token elements trigger consolidation candidates.
    """
    reports = [
        {
            'name': 'NIM Calculation Standard',
            'query': 'SELECT interest_income, interest_expense, earning_assets FROM branch_ledger',
            'columns': ['interest_income', 'interest_expense', 'earning_assets'],
            'usage': 100,
            'owner': 'Finance',
            'type': 'SQL Ledger'
        },
        {
            'name': 'ALCO Interest Yield Review',
            'query': 'SELECT interest_income, interest_expense, earning_assets, net_yield FROM branch_ledger',
            'columns': ['interest_income', 'interest_expense', 'earning_assets', 'net_yield'],
            'usage': 8,
            'owner': 'ALCO',
            'type': 'SQL Ledger'
        }
    ]
    
    results = await run_prism_workflow(reports)
    
    assert len(results['overlaps']) >= 1
    assert results['overlaps'][0]['reportA'] == 'NIM Calculation Standard'
    assert results['overlaps'][0]['reportB'] == 'ALCO Interest Yield Review'
    assert len(results['consolidationPlans']) >= 1
    assert results['consolidationPlans'][0]['similarity'] >= 60.0

@pytest.mark.anyio
async def test_run_prism_workflow_low_usage():
    """
    Verifies that reports with usage less than 15 are correctly highlighted as low usage.
    """
    reports = [
        {
            'name': 'Legacy Retail Default Tracker',
            'query': 'SELECT client_id, overdue_days FROM loans WHERE status = default',
            'columns': ['client_id', 'overdue_days'],
            'usage': 4,
            'owner': 'Retail Risk',
            'type': 'SQL Ledger'
        }
    ]
    
    results = await run_prism_workflow(reports)
    
    assert len(results['usageInsights']) == 1
    assert results['usageInsights'][0]['name'] == 'Legacy Retail Default Tracker'
    assert results['usageInsights'][0]['status'] == 'Audit Target (Low Usage)'

def test_parse_html_report():
    """
    Verifies that html text contents are parsed correctly into title, columns, and query snippets.
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Liquidity Coverage Ratios Executive Audit</title>
    </head>
    <body>
        <h2>Executive Briefing Card</h2>
        ID: <code>rep_liquidity_99a</code>
        <table>
            <thead>
                <tr>
                    <th>hqla_balance</th>
                    <th>cash_outflows</th>
                    <th>lcr_ratio</th>
                </tr>
            </thead>
            <tbody>
                <tr><td>150000</td><td>80000</td><td>1.87</td></tr>
            </tbody>
        </table>
        <code>SELECT hqla_balance, cash_outflows, lcr_ratio FROM liquidity_buffers</code>
    </body>
    </html>
    """
    
    parsed = parse_html_report(html_content, 'test_report.html')
    
    assert parsed['name'] == 'Liquidity Coverage Ratios Executive Audit'
    assert parsed['reportId'] == 'rep_liquidity_99a'
    assert 'hqla_balance' in parsed['columns']
    assert 'SELECT hqla_balance, cash_outflows' in parsed['query']
    assert parsed['type'] == 'HTML'
