"""
Product 4: Proactive Insights Alerts (Stateful Agentic AI)
Assigned Enterprise Agent: Proactive Monitor Agent
"""

import time
from typing import Dict, Any
from shared.intelligence import invoke_capability
from src.shared.infra.analytics_client import AnalyticsClient

_analytics_client = AnalyticsClient()
run_sqlite_query = _analytics_client.run_compatible_read_query

async def run_proactive_insights_workflow() -> Dict[str, Any]:
    print("[Workflow: Reporting - Proactive] Compiling proactive performance alerts stream.")

    from shared.session import get_profile_context_defaults

    # Dynamically fetch trends from the live Enterprise Ledger database records (no hardcoded fallback data)
    # 1. Dynamically retrieve active analyst context defaults
    defaults = get_profile_context_defaults()
    metric_id = defaults['metricId']
    metric_name = defaults['metricName']
    metric_val = defaults['metricValue']
    compare_val = defaults['compareValue']
    trends = defaults['trends']
    domain = defaults['business_domain']
    sme = defaults['sme']
    channel = defaults['channel']

    print(f"[Workflow: Reporting - Proactive] Compiling proactive alerts stream for domain: {domain}.")

    # 2. Run statistical metrics interpretation capability on defaults trends
    stats = await invoke_capability('metric_interpretation', {
        'metricId': metric_name,
        'trends': trends,
        'analysisType': 'anomaly'
    })

    alerts = []

    # 3. Formulate dynamic drift anomalies alerts if variance is calculated
    growth_rate = stats.get('growthRate', 0.0)
    direction = "Shift"
    if growth_rate > 0:
        direction = "Surge"
    elif growth_rate < 0:
        direction = "Decline"

    severity = 'High' if abs(growth_rate) > 5.0 else 'Medium'

    alerts.append({
        'metric': metric_name,
        'type': f'{direction} Anomaly Detected',
        'message': f'{metric_name} shifted from {compare_val} to {metric_val} in the latest cycle (growth: {growth_rate:.2f}%).',
        'recommendation': f'Execute {metric_name} Optimization Standard: Review operational boundaries and adjust model thresholds under supervision of SME {sme}.',
        'severity': severity
    })

    return {
        'alerts': alerts,
        'updatedAt': time.strftime('%H:%M:%S', time.localtime())
    }
