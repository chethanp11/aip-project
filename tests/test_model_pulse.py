"""
Unit tests for Product 16: Model Pulse (Stateful Agentic AI)
"""

import os
import sys
import pytest
from unittest.mock import AsyncMock, patch

# Ensure AIP/ and src/ are in path
aip_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../AIP"))
sys.path.insert(0, aip_root)
sys.path.insert(0, os.path.join(aip_root, "src"))

from src.data_science_ml.model_pulse.main import (
    run_model_pulse_workflow,
    PSI_WARNING_THRESHOLD,
    PSI_CRITICAL_THRESHOLD
)

@pytest.mark.anyio
@patch("src.data_science_ml.model_pulse.main.get_profile_context_defaults")
@patch("src.data_science_ml.model_pulse.main.call_llm")
async def test_model_pulse_workflow_stable(mock_call_llm, mock_defaults):
    """
    Verifies that Model Pulse correctly handles a stable model accuracy vector.
    """
    # Mock defaults
    mock_defaults.return_value = {
        'metricName': 'npl_ratio',
        'business_domain': 'Credit Portfolio Risk',
        'channel': '#alerts-credit-risk'
    }
    
    # Mock LLM dialogue
    mock_call_llm.return_value = None  # Will fall back to default dialogue structure
    
    # Input accuracy metrics: stable around champion baseline 0.93
    accuracy_metrics = [0.93, 0.93, 0.93, 0.93, 0.93]
    
    results = await run_model_pulse_workflow(accuracy_metrics)
    
    assert results['status'] == 'stable'
    assert results['driftScore'] == 0.0
    assert results['driftDetected'] is False
    assert results['psiScore'] == 0.0
    assert "Performance Stable" in results['explanation']

@pytest.mark.anyio
@patch("src.data_science_ml.model_pulse.main.get_profile_context_defaults")
@patch("src.data_science_ml.model_pulse.main.call_llm")
async def test_model_pulse_workflow_warning(mock_call_llm, mock_defaults):
    """
    Verifies that Model Pulse triggers warning status when PSI breaches the warning threshold.
    """
    mock_defaults.return_value = {
        'metricName': 'npl_ratio',
        'business_domain': 'Credit Portfolio Risk',
        'channel': '#alerts-credit-risk'
    }
    mock_call_llm.return_value = None
    
    # Input accuracy metrics: regressed slightly (drift_score = 0.05, psi_score = 0.14)
    # 0.14 >= PSI_WARNING_THRESHOLD (0.10) but < PSI_CRITICAL_THRESHOLD (0.25)
    accuracy_metrics = [0.93, 0.93, 0.93, 0.93, 0.88]
    
    results = await run_model_pulse_workflow(accuracy_metrics)
    
    assert results['status'] == 'warning'
    assert results['driftScore'] == 0.05
    assert results['driftDetected'] is True
    assert results['psiScore'] == 0.14
    assert "Concept Drift Warning" in results['explanation']

@pytest.mark.anyio
@patch("src.data_science_ml.model_pulse.main.get_profile_context_defaults")
@patch("src.data_science_ml.model_pulse.main.call_llm")
async def test_model_pulse_workflow_critical(mock_call_llm, mock_defaults):
    """
    Verifies that Model Pulse triggers critical status when PSI breaches the critical threshold.
    """
    mock_defaults.return_value = {
        'metricName': 'npl_ratio',
        'business_domain': 'Credit Portfolio Risk',
        'channel': '#alerts-credit-risk'
    }
    mock_call_llm.return_value = None
    
    # Input accuracy metrics: regressed significantly (drift_score = 0.10, psi_score = 0.28)
    # 0.28 >= PSI_CRITICAL_THRESHOLD (0.25)
    accuracy_metrics = [0.93, 0.93, 0.93, 0.93, 0.83]
    
    results = await run_model_pulse_workflow(accuracy_metrics)
    
    assert results['status'] == 'critical'
    assert results['driftScore'] == 0.10
    assert results['driftDetected'] is True
    assert results['psiScore'] == 0.28
    assert "Concept Drift Warning" in results['explanation']
