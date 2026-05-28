"""
Product 5: Insight Discovery (Stateful Agentic AI)
Assigned Banking Agent: Insight Discovery Agent
"""

from typing import List, Dict, Any
from shared.intelligence import invoke_capability

async def run_insight_discovery_workflow(segments_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    print("[Workflow: Analytics - Discovery] Surfacing banking segment micro-trends.")
    
    surfaced_insights = []

    for item in segments_data:
        cohort = item.get('cohort', 'Demographic Group')
        trends = item.get('timeline', []) or []
        
        interpreter = await invoke_capability('metric_interpretation', {
            'metricId': cohort,
            'trends': trends,
            'analysisType': 'anomaly'
        })

        growth_rate = interpreter.get('growthRate', 0.0)
        if abs(growth_rate) > 5.0:  # 5% shift is highly material in banking
            surfaced_insights.append({
                'cohort': cohort,
                'growthRate': growth_rate,
                'direction': 'Surging' if growth_rate > 0 else 'Declining',
                'explanation': interpreter.get('explanation', ''),
                'status': 'Material Discovery'
            })

    return {
        'insights': surfaced_insights,
        'totalScanned': len(segments_data)
    }
