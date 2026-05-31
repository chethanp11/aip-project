"""
Unit tests for checking browser caching prevention on static UI mounts.
"""

import os
import sys
import pytest

# Ensure AIP/ is current working directory so that relative static directories mount correctly
aip_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
original_cwd = os.getcwd()
os.chdir(aip_root)

# Ensure AIP/ and src/ are in path
sys.path.insert(0, aip_root)
sys.path.insert(0, os.path.join(aip_root, "src"))

from fastapi.testclient import TestClient
from src.main import app

def test_static_files_no_cache_headers():
    """
    Verifies that static file mounts are configured with NoCacheStaticFiles
    and return appropriate headers to completely prevent browser caching.
    """
    master_ui_dir = os.path.join(aip_root, "src/ui")
    os.makedirs(master_ui_dir, exist_ok=True)
    
    test_file_path = os.path.join(master_ui_dir, "test_cache.html")
    with open(test_file_path, "w") as f:
        f.write("<html><body>Test Caching</body></html>")
    
    try:
        client = TestClient(app)
        # Fetch the static file
        response = client.get("/test_cache.html")
        
        assert response.status_code == 200
        
        # Verify no-cache headers are present
        headers = response.headers
        assert headers.get("Cache-Control") == "no-store, no-cache, must-revalidate, max-age=0"
        assert headers.get("Pragma") == "no-cache"
        assert headers.get("Expires") == "0"
        
    finally:
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
        os.chdir(original_cwd)
