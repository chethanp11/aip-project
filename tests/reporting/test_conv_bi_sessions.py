"""
Unit and Integration tests for Conversational BI Session Storage & APIs.
"""

import os
import sys
import json
import shutil
import asyncio
import pytest
from unittest.mock import patch, AsyncMock

# Ensure AIP/ and src/ are in path
aip_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, aip_root)
sys.path.insert(0, os.path.join(aip_root, "src"))

from src.shared.config import config
from src.shared.infra_client.storage_client import StorageClient
from src.main import app
from fastapi.testclient import TestClient

client = TestClient(app)
HEADERS = {"Authorization": "Bearer AIP-TEST-SESSION-KEY"}

@pytest.fixture(autouse=True)
def setup_teardown_chats_dir():
    """Dynamically mocks storage path and cleans up test sessions."""
    test_chats_dir = os.path.join(config.STORAGE_ROOT, "test_chats")
    os.makedirs(test_chats_dir, exist_ok=True)
    
    # Patch get_chats_dir in main's _storage_client to use test dir
    with patch.object(StorageClient, "get_chats_dir", return_value=test_chats_dir):
        yield test_chats_dir
        
    # Clean up test files
    if os.path.exists(test_chats_dir):
        shutil.rmtree(test_chats_dir)


def test_storage_client_chats_dir():
    """Verifies that StorageClient correctly identifies and exposes get_chats_dir."""
    sc = StorageClient()
    assert sc.get_chats_dir() is not None
    assert os.path.isdir(sc.get_chats_dir())


def test_list_sessions_empty(setup_teardown_chats_dir):
    """Verifies GET /sessions returns an empty array when no chats have occurred."""
    res = client.get("/api/v1/workflows/reporting/conversational-bi/sessions", headers=HEADERS)
    assert res.status_code == 200
    assert res.json() == []


def test_list_sessions_ordered(setup_teardown_chats_dir):
    """Verifies GET /sessions correctly returns multiple saved session documents sorted by time."""
    test_dir = setup_teardown_chats_dir
    
    # Seed mock sessions
    s1 = {
        "sessionId": "session-1",
        "title": "Topic Alpha",
        "timestamp": "2026-05-30T09:00:00Z",
        "messages": []
    }
    s2 = {
        "sessionId": "session-2",
        "title": "Topic Beta",
        "timestamp": "2026-05-30T10:00:00Z",
        "messages": []
    }
    
    with open(os.path.join(test_dir, "session_session-1.json"), "w", encoding="utf-8") as f:
        json.dump(s1, f)
    with open(os.path.join(test_dir, "session_session-2.json"), "w", encoding="utf-8") as f:
        json.dump(s2, f)
        
    res = client.get("/api/v1/workflows/reporting/conversational-bi/sessions", headers=HEADERS)
    assert res.status_code == 200
    data = res.json()
    
    assert len(data) == 2
    # Sorted by timestamp descending (Topic Beta with 10:00 time first)
    assert data[0]["sessionId"] == "session-2"
    assert data[0]["title"] == "Topic Beta"
    assert data[1]["sessionId"] == "session-1"
    assert data[1]["title"] == "Topic Alpha"


def test_get_session_details_not_found(setup_teardown_chats_dir):
    """Verifies GET /sessions/{id} returns 404 for invalid session identifier."""
    res = client.get("/api/v1/workflows/reporting/conversational-bi/sessions/invalid-id", headers=HEADERS)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_get_session_details_success(setup_teardown_chats_dir):
    """Verifies GET /sessions/{id} returns the precise messages record."""
    test_dir = setup_teardown_chats_dir
    s = {
        "sessionId": "session-123",
        "title": "Yield analysis",
        "timestamp": "2026-05-30T10:15:00Z",
        "messages": [{"role": "user", "content": "Analyze branch yield"}]
    }
    
    with open(os.path.join(test_dir, "session_session-123.json"), "w", encoding="utf-8") as f:
        json.dump(s, f)
        
    res = client.get("/api/v1/workflows/reporting/conversational-bi/sessions/session-123", headers=HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["sessionId"] == "session-123"
    assert data["title"] == "Yield analysis"
    assert len(data["messages"]) == 1


@patch("src.main.run_conversational_bi_workflow", new_callable=AsyncMock)
def test_post_chat_saves_and_appends_session(mock_workflow, setup_teardown_chats_dir):
    """Verifies that sending a question automatically creates and updates a storage session JSON."""
    test_dir = setup_teardown_chats_dir
    
    # Mock workflow response
    mock_workflow.return_value = {
        "narrative": "BI result summary.",
        "renderedHtml": "<p>BI HTML summary</p>",
        "visualDecision": {"has_visual": False, "visuals": []},
        "vegaSpec": None
    }
    
    # First message: no sessionId passed -> generates new UUID session
    payload = {"question": "What is our balance by branch?"}
    res = client.post("/api/v1/workflows/reporting/conversational-bi", json=payload, headers=HEADERS)
    
    assert res.status_code == 200
    data = res.json()
    assert "sessionId" in data
    assert "sessionTitle" in data
    assert data["sessionTitle"] == "What is our balance by branch?"
    
    session_id = data["sessionId"]
    
    # Verify file saved physically to test storage chats folder
    session_file = os.path.join(test_dir, f"session_{session_id}.json")
    assert os.path.exists(session_file)
    
    with open(session_file, "r", encoding="utf-8") as f:
        stored = json.load(f)
        assert stored["sessionId"] == session_id
        assert len(stored["messages"]) == 2 # User message + Bot message
        assert stored["messages"][0]["role"] == "user"
        assert stored["messages"][0]["content"] == "What is our balance by branch?"
        assert stored["messages"][1]["role"] == "bot"
        assert stored["messages"][1]["content"] == "BI result summary."
        
    # Second message: pass the active sessionId -> appends to same JSON file
    payload2 = {
        "question": "What about active reserves?",
        "sessionId": session_id
    }
    
    # Update mock response for second step
    mock_workflow.return_value = {
        "narrative": "Reserves are stable.",
        "renderedHtml": "<p>Reserves stable</p>",
        "visualDecision": {"has_visual": False, "visuals": []},
        "vegaSpec": None
    }
    
    res2 = client.post("/api/v1/workflows/reporting/conversational-bi", json=payload2, headers=HEADERS)
    assert res2.status_code == 200
    
    with open(session_file, "r", encoding="utf-8") as f:
        stored2 = json.load(f)
        assert stored2["sessionId"] == session_id
        assert len(stored2["messages"]) == 4 # 2 turns -> 4 messages total
        assert stored2["messages"][2]["content"] == "What about active reserves?"
        assert stored2["messages"][3]["content"] == "Reserves are stable."
