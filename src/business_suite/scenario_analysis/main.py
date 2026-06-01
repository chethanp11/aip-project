"""
Product 7: What-if Analysis Sandbox (Stateful Agentic AI)
Assigned Enterprise Agent: What-if Simulator Agent
"""

from typing import Dict, Any
from src.shared.infra_client.analytics_client import AnalyticsClient

_analytics_client = AnalyticsClient()
get_lms_table = _analytics_client.get_table_rows

def run_whatif_workflow(earning_rate: str, resource_cost_rate: str, assets: str, npl_rate: str) -> Dict[str, Any]:
    print("[Workflow: Analytics - What-if] Simulating operational margins and portfolio profits.")

    # 1. Query Enterprise Ledger Tables to establish baseline balances if assets is omitted
    existing_tables = [t.lower() for t in _analytics_client.list_tables()]
    deposits_data = get_lms_table('deposits') if 'deposits' in existing_tables else []
    loans_data = get_lms_table('loans') if 'loans' in existing_tables else []

    lms_deposits_total = sum(d.get('amount', d.get('balance', 0)) for d in deposits_data) / 1000000000.0 if deposits_data else 0.0
    
    try:
        l_rate = float(earning_rate) if earning_rate else 6.5
        d_rate = float(resource_cost_rate) if resource_cost_rate else 2.5
        total_assets = float(assets) if assets else (lms_deposits_total / 0.90 if lms_deposits_total > 0 else 10.0)
        def_rate = float(npl_rate) if npl_rate else 1.5

        # Financial boundary sanity checks
        if l_rate < 0:
            l_rate = 6.5
        if d_rate < 0:
            d_rate = 2.5
        if total_assets <= 0:
            total_assets = 10.0
        if def_rate < 0:
            def_rate = 1.5
    except ValueError:
        l_rate = 6.5
        d_rate = 2.5
        total_assets = 10.0
        def_rate = 1.5

    # Convert assets from billions to dollars
    assets_in_dollars = total_assets * 1000000000.0

    # Active earning base is assumed to be 85% of assets
    earning_base = assets_in_dollars * 0.85
    # Baseline resource cost base is assumed to be 90% of assets
    resource_cost_base = assets_in_dollars * 0.90

    # Calculations:
    # 1. Projected Interest Revenue = earningBase * (lRate / 100)
    projected_revenue = round(earning_base * (l_rate / 100.0), 2)

    # 2. Projected Interest Expense = resourceCostBase * (dRate / 100)
    projected_expense = round(resource_cost_base * (d_rate / 100.0), 2)

    # 3. Projected Default Costs = earningBase * (defRate / 100) * 0.60 (60% Loss Given Default)
    projected_default = round(earning_base * (def_rate / 100.0) * 0.60, 2)

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
