"""
Product 7: What-if Analysis Sandbox (Stateful Agentic AI)
Assigned Enterprise Agent: What-if Simulator Agent
"""

from typing import Dict, Any
from src.shared.infra.analytics_client import AnalyticsClient

_analytics_client = AnalyticsClient()
get_lms_table = _analytics_client.get_table_rows

def run_whatif_workflow(loan_rate: str, deposit_rate: str, assets: str, npl_rate: str) -> Dict[str, Any]:
    print("[Workflow: Analytics - What-if] Simulating operational margins and portfolio profits.")

    # 1. Query Enterprise Ledger Tables to establish baseline balances if assets is omitted
    deposits_data = get_lms_table('deposits')
    loans_data = get_lms_table('loans')

    lms_deposits_total = sum(d.get('amount', d.get('balance', 0)) for d in deposits_data) / 1000000000.0 if deposits_data else 0.0
    
    try:
        l_rate = float(loan_rate) if loan_rate else 6.5
        d_rate = float(deposit_rate) if deposit_rate else 2.5
        total_assets = float(assets) if assets else (lms_deposits_total / 0.90 if lms_deposits_total > 0 else 10.0)
        def_rate = float(npl_rate) if npl_rate else 1.5
    except ValueError:
        l_rate = 6.5
        d_rate = 2.5
        total_assets = 10.0
        def_rate = 1.5

    # Convert assets from billions to dollars
    assets_in_dollars = total_assets * 1000000000.0

    # Active earning assets (e.g. loans) is assumed to be 85% of assets
    loan_portfolio = assets_in_dollars * 0.85
    # Core deposit liabilities is assumed to be 90% of assets
    deposit_liabilities = assets_in_dollars * 0.90

    # Calculations:
    # 1. Projected Interest Revenue = loanPortfolio * (lRate / 100)
    projected_revenue = round(loan_portfolio * (l_rate / 100.0), 2)

    # 2. Projected Interest Expense = depositLiabilities * (dRate / 100)
    projected_expense = round(deposit_liabilities * (d_rate / 100.0), 2)

    # 3. Projected Default Costs = loanPortfolio * (defRate / 100) * 0.60 (60% Loss Given Default)
    projected_default = round(loan_portfolio * (def_rate / 100.0) * 0.60, 2)

    # 4. Net Spread Profit = Revenue - Expense - Default Costs
    net_spread = round(projected_revenue - projected_expense - projected_default, 2)

    # 5. NIM = (Revenue - Expense) / assetsInDollars * 100
    net_interest_margin = round(((projected_revenue - projected_expense) / assets_in_dollars * 100.0), 2) if assets_in_dollars > 0 else 0.0

    return {
        'projectedInterestRevenue': projected_revenue,
        'projectedInterestExpense': projected_expense,
        'projectedDefaultCosts': projected_default,
        'netSpreadProfit': net_spread,
        'netInterestMargin': net_interest_margin
    }
