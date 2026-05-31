"""
AIP Intelligence Layer & Shared Capabilities Registry (Python)

Provides centralized routing, capability registration, dynamic invocation,
thread-safe request context tracking, and trace logging audits.
"""

import os
import time
import random
import string
import urllib.request
import json
from contextvars import ContextVar
from typing import Callable, Dict, Any, List, Optional

# Thread-safe request-scoped context tracking
# Holds: {'agent': str, 'api_key': str}
active_agent_context: ContextVar[Dict[str, str]] = ContextVar(
    'active_agent_context',
    default={'agent': 'Platform Routing Agent', 'api_key': ''}
)

# ==========================================================================
# ⚙️ ZERO-DEPENDENCY NATIVE .ENV LOADER
# ==========================================================================
def load_dotenv():
    try:
        # Find the workspace root or external secrets .env file
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        env_path = os.path.join(base_dir, 'Infra', 'secrets', '.env')
        
        # Fallback: check workspace root or current directory
        if not os.path.exists(env_path):
            env_path = os.path.join(base_dir, '.env')
        if not os.path.exists(env_path):
            env_path = os.path.abspath('.env')
            
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    trimmed = line.strip()
                    if not trimmed or trimmed.startswith('#'):
                        continue
                    if '=' in trimmed:
                        key, val = trimmed.split('=', 1)
                        key = key.strip()
                        val = val.strip()
                        # Remove quotes
                        if val.startswith('"') and val.endswith('"'):
                            val = val[1:-1]
                        elif val.startswith("'") and val.endswith("'"):
                            val = val[1:-1]
                        os.environ[key] = val.strip()
            print(f'[Intelligence] Processed local environment configs successfully from: {env_path}')
    except Exception as e:
        print(f'[Intelligence] Reliance on system environment variables, local .env parse failed: {str(e)}')

load_dotenv()

# In-memory capability registry and execution logs
capability_registry: Dict[str, Dict[str, Any]] = {}
execution_logs: List[Dict[str, Any]] = []

# ==========================================================================
# 🔌 CAPABILITY REGISTRATION & ROUTING
# ==========================================================================
def register_capability(name: str, config: Dict[str, Any], handler: Callable[[Dict[str, Any]], Any]):
    """Registers an atomic stateless capability."""
    if name in capability_registry:
        print(f'[Intelligence] Overwriting registered capability: {name}')
    
    capability_registry[name] = {
        'name': name,
        'description': config.get('description', ''),
        'inputSchema': config.get('inputSchema', {}),
        'outputSchema': config.get('outputSchema', {}),
        'handler': handler
    }
    print(f'[Intelligence] Capability registered successfully: {name}')

import inspect

async def invoke_capability(name: str, input_params: Dict[str, Any]) -> Any:
    """Dynamically invokes a capability, capturing audit telemetry traces."""
    capability = capability_registry.get(name)
    if not capability:
        raise ValueError(f"Capability not found in registry: {name}")

    start_time = time.time()
    context = active_agent_context.get()
    current_agent = context.get('agent', 'Platform Routing Agent')
    print(f"[Intelligence] Invoking capability: {name} (Executing Agent: {current_agent})")

    try:
        # Run capability handler (can support sync or async)
        handler = capability['handler']
        if inspect.iscoroutinefunction(handler):
            result = await handler(input_params)
        else:
            result = handler(input_params)
            if inspect.iscoroutine(result):
                result = await result
                
        duration_ms = int((time.time() - start_time) * 1000)
        log_execution(name, input_params, result, duration_ms, 'completed')
        return result
    except Exception as error:
        duration_ms = int((time.time() - start_time) * 1000)
        log_execution(name, input_params, {'error': str(error)}, duration_ms, 'failed')
        raise error

def list_capabilities() -> List[Dict[str, Any]]:
    """Lists all capabilities currently registered in the registry."""
    return [
        {
            'name': cap['name'],
            'description': cap['description'],
            'inputSchema': cap['inputSchema'],
            'outputSchema': cap['outputSchema']
        }
        for cap in capability_registry.values()
    ]

# ==========================================================================
# 📊 TELEMETRY AUDIT LOGS PERSISTENCE
# ==========================================================================
def log_execution(capability: str, input_params: Dict[str, Any], output_params: Dict[str, Any], duration_ms: int, status: str):
    """Audits and logs a capability execution run."""
    context = active_agent_context.get()
    calling_agent = context.get('agent', 'Platform Routing Agent')
    api_key = context.get('api_key', '')

    # Mask API Key (e.g. AIP-BANK-SECURE-2026 -> AIP-BA***)
    masked_key = 'No Key'
    if api_key and api_key.startswith('AIP-'):
        masked_key = api_key[:6] + '***'

    # Generate unique log ID
    log_id = 'log_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=9))

    log_entry = {
        'id': log_id,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'capability': capability,
        'input': input_params,
        'output': output_params,
        'durationMs': duration_ms,
        'status': status,
        'agent': calling_agent,
        'apiKey': masked_key
    }
    execution_logs.append(log_entry)
    print(f"[Intelligence Audit] Capability: {capability} | Agent: {calling_agent} | Key: {masked_key} | Duration: {duration_ms}ms | Status: {status}")

def get_logs() -> List[Dict[str, Any]]:
    """Retrieves all execution logs."""
    return execution_logs

def clear_logs() -> bool:
    """Purges all execution trace logs."""
    execution_logs.clear()
    return True

# ==========================================================================
# 🚀 NATIVE OPENAI LLM API CLIENT
# ==========================================================================
async def call_llm(system_prompt: str, user_prompt: str, json_mode: bool = False) -> Optional[str]:
    """
    Triggers live GPT completion query calls to the OpenAI endpoint using urllib.
    """
    load_dotenv()
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key or api_key.strip() == '' or api_key == 'your_openai_api_key_here':
        print('[Intelligence AI] Live OpenAI API Key missing or default placeholder, using mock heuristics.')
        return None

    try:
        start_time = time.time()
        url = 'https://api.openai.com/v1/chat/completions'
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        payload = {
            'model': 'gpt-4o-mini',
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            'temperature': 0.1
        }
        if json_mode:
            payload['response_format'] = {'type': 'json_object'}
            
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        
        with urllib.request.urlopen(req, timeout=60) as response:
            res_body = response.read().decode('utf-8')
            res_data = json.loads(res_body)
            duration_ms = int((time.time() - start_time) * 1000)
            
            tokens = res_data.get('usage', {}).get('total_tokens', 0)
            print(f"[Intelligence AI] OpenAI call succeeded in {duration_ms}ms (tokens: {tokens})")
            return res_data['choices'][0]['message']['content']
            
    except Exception as e:
        print(f'[Intelligence AI] OpenAI fetch exception: {str(e)}')
        return None
