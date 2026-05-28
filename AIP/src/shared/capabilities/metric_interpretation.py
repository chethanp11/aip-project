"""
Metric Interpretation Capability
"""

import math
from typing import Dict, Any

config = {
    'description': 'Executes Z-score anomaly scans, percentage growth rates, and contributor driver analyses on metric datasets.',
    'inputSchema': {
        'metricId': 'string',
        'trends': 'array of numbers',
        'analysisType': 'string (anomaly, variance)'
    },
    'outputSchema': {
        'growthRate': 'number',
        'anomalies': 'array of indices',
        'explanation': 'string',
        'statistics': 'object'
    }
}

def handler(input_params: Dict[str, Any]) -> Dict[str, Any]:
    trends = input_params.get('trends', []) or []
    metric_id = input_params.get('metricId', 'Metric') or 'Metric'
    
    if not trends:
        return {
            'growthRate': 0,
            'anomalies': [],
            'explanation': 'No historical trends available to analyze.',
            'statistics': {}
        }
        
    # 1. Calculate growth rate
    growth_rate = 0.0
    if len(trends) > 1:
        latest = trends[-1]
        previous = trends[-2]
        if previous != 0:
            growth_rate = round(((latest - previous) / previous) * 100, 2)
            
    # 2. Compute statistics: Mean, Standard Deviation, and Z-Scores
    mean = sum(trends) / len(trends)
    variance = sum((v - mean) ** 2 for v in trends) / len(trends)
    std_dev = math.sqrt(variance) if variance > 0 else 1.0
    
    anomalies = []
    for idx, val in enumerate(trends):
        z_score = (val - mean) / std_dev
        if abs(z_score) > 1.5:  # lower threshold for MVP visibility
            anomalies.append({
                'index': idx,
                'value': val,
                'zScore': round(z_score, 2)
            })
            
    # 3. Draft business explanations
    explanation = f"The metric {metric_id} changed by {growth_rate}% in the latest period. "
    if anomalies:
        latest_anomaly = anomalies[-1]
        explanation += f"🚨 Critical anomaly detected at data index {latest_anomaly['index']} with value {latest_anomaly['value']} (Z-Score: {latest_anomaly['zScore']} std devs)."
    else:
        explanation += "✅ No statistical anomalies flagged. Metric fluctuations reside within normal baseline distributions."
        
    return {
        'growthRate': growth_rate,
        'anomalies': anomalies,
        'explanation': explanation,
        'statistics': {
            'mean': round(mean, 2),
            'stdDev': round(std_dev, 2),
            'variance': round(variance, 2)
        }
    }
