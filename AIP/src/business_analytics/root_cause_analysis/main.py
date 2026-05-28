"""
Product 6: Root Cause Analysis (Stateful Agentic AI)
Assigned Banking Agent: RCA Diagnostic Agent
"""

from typing import List, Dict, Any
from shared.intelligence import invoke_capability, call_llm

async def run_rca_workflow(dataset_name: str, metrics_data: List[Dict[str, Any]], prompt: str = "") -> Dict[str, Any]:
    print(f"[Workflow: Analytics - RCA] Running RCA drivers scan for banking portfolio: {dataset_name}")

    row_count = len(metrics_data)
    missing_values = 0
    
    for row in metrics_data:
        for val in row.values():
            if val is None or val == '':
                missing_values += 1

    trend_vector = [row.get('value', 0) or 0 for row in metrics_data]
    interpretation = await invoke_capability('metric_interpretation', {
        'metricId': dataset_name,
        'trends': trend_vector,
        'analysisType': 'anomaly'
    })

    contributions = {}
    for row in metrics_data:
        segment = row.get('segment', 'Unknown Portfolio Segment') or 'Unknown Portfolio Segment'
        val = row.get('value', 0) or 0
        contributions[segment] = contributions.get(segment, 0.0) + val

    sorted_segments = [
        {'segment': k, 'value': round(v, 2)}
        for k, v in contributions.items()
    ]
    sorted_segments.sort(key=lambda x: x['value'], reverse=True)

    primary_driver = f"{sorted_segments[0]['segment']} (Total: {sorted_segments[0]['value']})" if sorted_segments else 'Unknown Driver'

    # Attempt to query live LLM for executive analysis narrative
    system_prompt = "You are a professional banking risk auditor specializing in Root Cause Analysis (RCA). Compile a concise, executive-grade diagnostic narrative summarizing portfolio asset/liability drivers variance."
    
    user_prompt = f"""RCA Scan Report for dataset: {dataset_name}
- Total Audited Entries: {row_count}
- Detected Missing Data Cells: {missing_values}
- Portfolio Segments Performance contributions: {sorted_segments}
- Primary Identified Driver: {primary_driver}
- Statistical anomalies and baseline shifts: {interpretation.get('explanation', '')}
- Growth rate computed: {interpretation.get('growthRate', 0)}%"""
    if prompt:
        user_prompt += f"\n- Additional Analyst Directives: {prompt}"
    user_prompt += "\n\nProvide a highly coherent, structured analysis summary in clean markdown format."

    ai_narrative = await call_llm(system_prompt, user_prompt)
    if ai_narrative:
        tailored_narrative = ai_narrative.strip()
    else:
        generate_result = await invoke_capability('narrative_generation', {
            'templateId': 'rca_template',
            'variables': {
                'metricName': dataset_name,
                'missingCount': str(missing_values),
                'featureSuggestion': 'Recommend clustering branches by local interest rate sensitivity.' if row_count > 5 else 'Recommend standard LDR tracking.',
                'driversList': f"Primary portfolio segment driver identified as: '{primary_driver}'. Growth rate of overall trend: {interpretation.get('growthRate', 0)}%.",
                'summary': interpretation.get('explanation', '')
            }
        })
        tailored_narrative = generate_result.get('narrative', '')

    return {
        'profiling': {
            'rowCount': row_count,
            'missingValues': missing_values,
            'summary': f"Analyzed {row_count} ledger entries. Detected {missing_values} missing values across dimensions."
        },
        'drivers': sorted_segments,
        'primaryDriver': primary_driver,
        'narrative': tailored_narrative
    }
