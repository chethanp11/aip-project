"""
Product 4: Proactive Insights Alerts (Stateful Agentic AI)
Assigned Banking Agent: Proactive Monitor Agent
"""

import time
from typing import Dict, Any
from shared.intelligence import invoke_capability

async def run_proactive_insights_workflow() -> Dict[str, Any]:
    print("[Workflow: Reporting - Proactive] Compiling proactive banking alerts stream.")

    nim_trends = [3.12, 3.08, 3.15, 2.95, 2.88, 2.82, 2.65]
    npl_trends = [1.42, 1.45, 1.38, 1.49, 1.55, 1.62, 1.85]

    nim_stats = await invoke_capability('metric_interpretation', {
        'metricId': 'Net Interest Margin (NIM)',
        'trends': nim_trends,
        'analysisType': 'anomaly'
    })

    npl_stats = await invoke_capability('metric_interpretation', {
        'metricId': 'Non-Performing Loans (NPL) Ratio',
        'trends': npl_trends,
        'analysisType': 'anomaly'
    })

    alerts = []

    if nim_stats.get('anomalies', []):
        alerts.append({
            'metric': 'Net Interest Margin (NIM)',
            'type': 'Negative Shift Anomaly',
            'message': 'Net Interest Margin compressed significantly below standard Z-score limits (Value: 2.65%).',
            'recommendation': 'Initiate NIM Squeeze Playbook: review interest sensitivity duration gaps and adjust deposits funding yield caps.',
            'severity': 'High'
        })

    if npl_stats.get('anomalies', []):
        alerts.append({
            'metric': 'Non-Performing Loans (NPL) Ratio',
            'type': 'Trend Surge Warning',
            'message': 'NPL Ratio surged MoM by over 14% to 1.85% in latest loan cohort.',
            'recommendation': 'Execute NPL Risk Mitigation Standard: review credit score classifier thresholds for applicants scoring below 650.',
            'severity': 'High'
        })

    return {
        'alerts': alerts,
        'updatedAt': time.strftime('%H:%M:%S', time.localtime())
    }
