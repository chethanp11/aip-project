"""
AIP In-Memory Session Manager
"""

import time
from typing import Dict, Any

active_sessions: Dict[str, Dict[str, Any]] = {}

def get_session(session_id: str) -> Dict[str, Any]:
    """Retrieves or creates a session by ID."""
    if session_id not in active_sessions:
        active_sessions[session_id] = {
            'id': session_id,
            'created': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'filters': {'period': 'Q1-2026'}
        }
    return active_sessions[session_id]

def set_session(session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Updates and saves a session payload."""
    session = get_session(session_id)
    session.update(payload)
    session['updated'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    active_sessions[session_id] = session
    return session

def clear_session(session_id: str) -> bool:
    """Removes an active session."""
    if session_id in active_sessions:
        del active_sessions[session_id]
        return True
    return False
