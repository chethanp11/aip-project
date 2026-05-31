"""
Context Management Capability
"""

from typing import Dict, Any
from shared.session import get_session, set_session, clear_session

config = {
    'description': 'Stateless adapter to read and write temporary analytical variables for user sessions.',
    'inputSchema': {
        'sessionId': 'string',
        'action': 'string (get, set, clear)',
        'payload': 'object (optional)'
    },
    'outputSchema': {
        'success': 'boolean',
        'sessionState': 'object'
    }
}

def handler(input_params: Dict[str, Any]) -> Dict[str, Any]:
    session_id = input_params.get('sessionId')
    action = input_params.get('action')
    payload = input_params.get('payload', {})
    
    if not session_id:
        raise ValueError("Missing sessionId in context management request.")
        
    if action == 'get':
        state = get_session(session_id)
        return {'success': True, 'sessionState': state}
    elif action == 'set':
        state = set_session(session_id, payload)
        return {'success': True, 'sessionState': state}
    elif action == 'clear':
        success = clear_session(session_id)
        return {'success': success, 'sessionState': {}}
    else:
        raise ValueError(f"Unsupported context action: {action}")
