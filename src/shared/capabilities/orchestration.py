"""
Orchestration Capability (Async)
"""

import time
from typing import Dict, Any

config = {
    'description': 'Sequentially executes modular capability steps in a workflow pipeline, returning execution traces.',
    'inputSchema': {
        'steps': 'array of objects'
    },
    'outputSchema': {
        'success': 'boolean',
        'traces': 'array of objects'
    }
}

async def handler(input_params: Dict[str, Any]) -> Dict[str, Any]:
    from shared.intelligence import invoke_capability
    
    steps = input_params.get('steps', []) or []
    traces = []
    success = True
    
    print(f"[Orchestrator] Executing custom DAG with {len(steps)} sequential nodes.")
    
    for step in steps:
        step_start_time = time.time()
        step_id = step.get('id', 'step')
        cap_name = step.get('capability')
        step_input = step.get('input', {})
        
        try:
            print(f"[Orchestrator] Executing node: {step_id} (Capability: {cap_name})")
            output = await invoke_capability(cap_name, step_input)
            
            duration_ms = int((time.time() - step_start_time) * 1000)
            traces.append({
                'stepId': step_id,
                'capability': cap_name,
                'status': 'completed',
                'durationMs': duration_ms,
                'output': output
            })
        except Exception as err:
            success = False
            duration_ms = int((time.time() - step_start_time) * 1000)
            traces.append({
                'stepId': step_id,
                'capability': cap_name,
                'status': 'failed',
                'durationMs': duration_ms,
                'error': str(err)
            })
            print(f"[Orchestrator] Node {step_id} failed execution: {str(err)}. Terminating sequence.")
            break
            
    return {
        'success': success,
        'traces': traces
    }
