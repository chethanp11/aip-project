from pathlib import Path
import shutil
import subprocess

import pytest


def test_micro_frontends_use_same_origin_api_paths():
    """Embedded UIs must not call a hardcoded host that loses the active login origin."""
    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / "src"

    checked_files = [
        path
        for path in src_root.rglob("ui/index.html")
        if path != src_root / "ui" / "index.html"
    ]

    assert checked_files
    for path in checked_files:
        content = path.read_text()
        assert "http://localhost:8000/api/v1" not in content, str(path)


def test_micro_frontends_do_not_call_apis_before_token_is_available():
    """Embedded UIs can load before shell login, but protected API calls must wait."""
    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / "src"

    checked_files = [
        path
        for path in src_root.rglob("ui/index.html")
        if path != src_root / "ui" / "index.html"
    ]

    assert checked_files
    for path in checked_files:
        content = path.read_text()
        if "Authed Fetch Interceptor" not in content:
            continue
        assert "resolveAipToken" in content, str(path)
        assert "Authentication token is not available yet." in content, str(path)


def test_shell_javascript_is_parseable():
    """A shell syntax error prevents the login handler from binding."""
    if not shutil.which("node"):
        pytest.skip("node is required for JavaScript syntax validation")

    repo_root = Path(__file__).resolve().parents[1]
    shell_js = repo_root / "src" / "ui" / "index.js"

    result = subprocess.run(
        ["node", "--check", str(shell_js)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_shell_home_uses_revised_persona_products():
    """Shell home and nav should reflect revised AIP products instead of legacy suite tiles."""
    repo_root = Path(__file__).resolve().parents[1]
    shell_html = (repo_root / "src" / "ui" / "index.html").read_text()
    shell_js = (repo_root / "src" / "ui" / "index.js").read_text()

    removed_banner_labels = ["Application Suites", "Knowledge Layer", "Enterprise Data Access"]
    for label in removed_banner_labels:
        assert label not in shell_html

    business_products = [
        "dashboards",
        "conversational-bi",
        "proactive-alerts",
        "deep-insights",
        "scenario-analysis",
    ]
    analyst_products = [
        "prism",
        "research",
        "explore-data",
        "build-report",
        "root-cause-analysis",
        "recommend-actions",
    ]

    for product_id in business_products + analyst_products:
        assert f"page-{product_id}" in shell_html
        assert f"'{product_id}'" in shell_js

    assert "Reporting Suite</span>" not in shell_html
    assert "Business Analytics</span>" not in shell_html
    assert "Database Explorer" not in shell_html
    assert "page-db-explorer" not in shell_html



def test_research_micro_frontend_exists():
    repo_root = Path(__file__).resolve().parents[1]
    research_ui = repo_root / "src" / "analyst_actions" / "research" / "ui"

    assert (research_ui / "index.html").exists()
    assert (research_ui / "index.css").exists()
    assert (research_ui / "index.js").exists()
    assert "/workflows/analyst/research" in (research_ui / "index.js").read_text()
