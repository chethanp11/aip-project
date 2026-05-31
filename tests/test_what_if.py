"""
Unit tests for Product 7: What-if Analysis Sandbox (Stateful Agentic AI)
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Ensure AIP/ and src/ are in path
aip_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, aip_root)
sys.path.insert(0, os.path.join(aip_root, "src"))

from src.business_suite.scenario_analysis.main import run_whatif_workflow

@patch("src.business_suite.scenario_analysis.main.get_lms_table")
def test_run_whatif_workflow_standard(mock_get_table):
    """
    Verifies that the What-If sandbox computes correct projections with standard valid inputs.
    """
    mock_get_table.return_value = [] # Ensure deposits total resolves to 0.0, using assets fallback
    
    # 6.5% earning, 2.5% cost, 10.0 billion assets, 1.5% defaults
    # assets_in_dollars = 10,000,000,000
    # earning_base = 8,500,000,000
    # resource_cost_base = 9,000,000,000
    # projected_revenue = 8,500,000,000 * 0.065 = 552,500,000
    # projected_expense = 9,000,000,000 * 0.025 = 225,000,000
    # projected_default = 8,500,000,000 * 0.015 * 0.60 = 76,500,000
    # net_spread = 552,500,000 - 225,000,000 - 76,500,000 = 251,000,000
    # nim = (552,500,000 - 225,000,000) / 10,000,000,000 * 100 = 3.275 -> 3.28
    
    results = run_whatif_workflow("6.5", "2.5", "10.0", "1.5")
    
    assert results['projectedInterestRevenue'] == 552500000.0
    assert results['projectedInterestExpense'] == 225000000.0
    assert results['projectedDefaultCosts'] == 76500000.0
    assert results['netSpreadProfit'] == 251000000.0
    assert results['netInterestMargin'] == 3.28

@patch("src.business_suite.scenario_analysis.main.get_lms_table")
def test_run_whatif_workflow_value_error_fallback(mock_get_table):
    """
    Verifies that formatting errors cleanly fall back to baselines.
    """
    mock_get_table.return_value = []
    
    results = run_whatif_workflow("abc", "xyz", "invalid", "npl")
    
    # Should fall back to standard 6.5, 2.5, 10.0, 1.5 values
    assert results['projectedInterestRevenue'] == 552500000.0
    assert results['netInterestMargin'] == 3.28

@patch("src.business_suite.scenario_analysis.main.get_lms_table")
def test_run_whatif_workflow_boundary_negative_fallback(mock_get_table):
    """
    Verifies that negative values are overridden to standard baseline parameters.
    """
    mock_get_table.return_value = []
    
    # Passing negative rates/assets
    results = run_whatif_workflow("-5.0", "-1.0", "-20.0", "-3.0")
    
    # All negative rates/assets should trigger baseline fallbacks
    assert results['projectedInterestRevenue'] == 552500000.0
    assert results['projectedInterestExpense'] == 225000000.0
    assert results['netSpreadProfit'] == 251000000.0
    assert results['netInterestMargin'] == 3.28
