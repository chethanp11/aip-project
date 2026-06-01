"""
Unit tests for request-scoped OpenAI API Key injection and sk- Bearer token authentication.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Ensure AIP/ and src/ are in path
aip_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, aip_root)
sys.path.insert(0, os.path.join(aip_root, "src"))

from src.main import app
from shared.intelligence import active_agent_context, call_llm
from kms.index import get_openai_embedding

def test_sk_bearer_token_authorization():
    """
    Verifies that a Bearer token starting with sk- is accepted as valid,
    creates a session, and places the key in active_agent_context.
    """
    client = TestClient(app)
    
    # We will mock the actual endpoint execution to just inspect active_agent_context
    headers = {
        "Authorization": "Bearer sk-proj-testkey1234567890abcdef"
    }
    
    # Make request to a protected endpoint (e.g. analytics-data/tables)
    # We mock list_tables so the endpoint runs smoothly and we can verify context
    with patch("src.main.analytics_client.list_tables", return_value=["test_table"]) as mock_list:
        response = client.get("/api/v1/analytics-data/tables", headers=headers)
        assert response.status_code == 200
        mock_list.assert_called_once()
        
        # Verify that session was registered for the sk- key
        from shared.session import active_sessions
        assert "sk-proj-testkey1234567890abcdef" in active_sessions
        session = active_sessions["sk-proj-testkey1234567890abcdef"]
        assert session["role"] == "Analyst"
        assert session["display_name"] == "OpenAI Agent Console"

def test_custom_openai_key_headers():
    """
    Verifies that standard session token (AIP-) with X-OpenAI-API-Key header
    correctly injects the OpenAI key into the request-scoped context.
    """
    client = TestClient(app)
    
    # Register a standard session
    from shared.session import set_session
    set_session("AIP-ANALYST-SESSION-TESTKEY", {
        "username": "test_user",
        "role": "Analyst",
        "clearance": "Internal",
        "display_name": "Test User",
        "allowed_tables": ["test_table"]
    })
    
    headers = {
        "Authorization": "Bearer AIP-ANALYST-SESSION-TESTKEY",
        "X-OpenAI-API-Key": "sk-custom-header-key"
    }
    
    # We want to capture the thread-scoped active_agent_context during the request.
    # To do this, we patch list_tables to read and return active_agent_context.get()
    def mock_list_tables():
        ctx = active_agent_context.get()
        return [ctx.get("openai_api_key"), ctx.get("api_key")]
        
    with patch("src.main.analytics_client.list_tables", side_effect=mock_list_tables):
        response = client.get("/api/v1/analytics-data/tables", headers=headers)
        assert response.status_code == 200
        res_data = response.json()
        assert res_data == ["sk-custom-header-key", "AIP-ANALYST-SESSION-TESTKEY"]

import asyncio

def test_call_llm_picks_up_request_context_key():
    """
    Verifies that call_llm prioritizes active_agent_context key over os.environ.
    """
    # 1. Set the key in context
    token = active_agent_context.set({
        "agent": "Test Agent",
        "api_key": "dummy",
        "openai_api_key": "sk-context-scoped-key"
    })
    
    async def run_test():
        # Mock urllib request to verify it uses the correct authorization header
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"choices": [{"message": {"content": "Hello World"}}], "usage": {}}'
            mock_urlopen.return_value.__enter__.return_value = mock_response
            
            # Run call_llm
            res = await call_llm("system", "user")
            
            assert res == "Hello World"
            # Verify the call was made with our request-scoped context key
            called_args = mock_urlopen.call_args[0]
            req = called_args[0]
            assert req.headers["Authorization"] == "Bearer sk-context-scoped-key"

    try:
        asyncio.run(run_test())
    finally:
        active_agent_context.reset(token)

def test_get_openai_embedding_picks_up_request_context_key():
    """
    Verifies that get_openai_embedding prioritizes active_agent_context key.
    """
    # Set key in context
    token = active_agent_context.set({
        "agent": "Test Agent",
        "api_key": "dummy",
        "openai_api_key": "sk-emb-context-scoped-key"
    })
    
    try:
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"data": [{"embedding": [0.1, 0.2, 0.3]}]}'
            mock_urlopen.return_value.__enter__.return_value = mock_response
            
            res = get_openai_embedding("text")
            
            assert res == [0.1, 0.2, 0.3]
            # Verify authorization header
            called_args = mock_urlopen.call_args[0]
            req = called_args[0]
            assert req.headers["Authorization"] == "Bearer sk-emb-context-scoped-key"
    finally:
        active_agent_context.reset(token)
