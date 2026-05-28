"""
Visualization Capability
"""

from typing import Dict, Any

config = {
    'description': 'Compiles raw historical arrays and chart choices into standardized Vega-Lite JSON specs.',
    'inputSchema': {
        'chartType': 'string (bar, line)',
        'trends': 'array of numbers',
        'labels': 'array of strings (optional)'
    },
    'outputSchema': {
        'vegaSpec': 'object'
    }
}

def handler(input_params: Dict[str, Any]) -> Dict[str, Any]:
    trends = input_params.get('trends', []) or []
    chart_type = input_params.get('chartType', 'line') or 'line'
    
    labels = input_params.get('labels')
    if not labels:
        labels = [f"P-{idx + 1}" for idx in range(len(trends))]
        
    values = []
    for idx, val in enumerate(trends):
        label = labels[idx] if idx < len(labels) else f"P-{idx + 1}"
        values.append({
            'period': label,
            'value': val
        })
        
    vega_spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "AIP Auto Generated Spec",
        "width": "container",
        "height": 220,
        "data": {
            "values": values
        },
        "mark": 'bar' if chart_type == 'bar' else 'line',
        "encoding": {
            "x": {
                "field": "period",
                "type": "nominal",
                "axis": { "labelAngle": 0 }
            },
            "y": {
                "field": "value",
                "type": "quantitative"
            }
        }
    }
    
    return {
        'vegaSpec': vega_spec
    }
