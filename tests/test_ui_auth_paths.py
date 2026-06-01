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


def test_kms_micro_frontend_javascript_is_parseable_and_avoids_api_base_collision():
    """KMS external JS must not redeclare the inline auth interceptor API_BASE constant."""
    if not shutil.which("node"):
        pytest.skip("node is required for JavaScript syntax validation")

    repo_root = Path(__file__).resolve().parents[1]
    kms_js = repo_root / "src" / "kms" / "ui" / "index.js"
    kms_html = (repo_root / "src" / "kms" / "ui" / "index.html").read_text()
    kms_js_content = kms_js.read_text()

    result = subprocess.run(
        ["node", "--check", str(kms_js)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "const API_BASE" in kms_html
    assert "const API_BASE" not in kms_js_content
    assert "KMS_API_BASE" in kms_js_content


def test_shell_logout_and_button_feedback_are_bound():
    repo_root = Path(__file__).resolve().parents[1]
    shell_js = (repo_root / "src" / "ui" / "index.js").read_text()

    assert "shell-logout-btn" in shell_js
    assert "Logout in progress" in shell_js
    assert "initGlobalButtonFeedback" in shell_js
    assert "is-clicked" in shell_js


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



def test_shell_product_and_system_pages_have_consistent_headers():
    repo_root = Path(__file__).resolve().parents[1]
    shell_html = (repo_root / "src" / "ui" / "index.html").read_text()

    pages = [
        "dashboards",
        "conversational-bi",
        "proactive-alerts",
        "deep-insights",
        "scenario-analysis",
        "prism",
        "research",
        "explore-data",
        "build-report",
        "root-cause-analysis",
        "recommend-actions",
        "kms",
    ]

    for page in pages:
        section_start = shell_html.index(f'id="page-{page}"')
        section_end = shell_html.index("</section>", section_start)
        section = shell_html[section_start:section_end]
        assert 'class="platform-page-header"' in section, page
        assert 'platform-page-eyebrow' in section, page
        assert 'platform-page-status' in section, page

    assert shell_html.count('class="platform-page-header"') >= len(pages)



def test_micro_frontends_do_not_render_duplicate_product_headers():
    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / "src"
    duplicate_header_text = [
        "Proactive Alerts & Monitoring Console",
        "Continuous background analysis of operational exception metrics",
        "Insight Discovery Exploratory Canvas",
        "What-If Scenario Sandbox",
        "PRISM Catalog & Schema Rationalizer",
        "Chief Communications narratives & Storytelling",
        "RCA Diagnostics & Driver Deconstruction",
        "Conversational BI Assistant</h2>",
        "Reporting Workspace</h1>",
        "<h1>Research</h1>",
        "KMS Grounding Workspace</h2>",
    ]

    checked_files = [
        path
        for path in src_root.rglob("ui/index.html")
        if path != src_root / "ui" / "index.html"
    ]

    for path in checked_files:
        content = path.read_text()
        for duplicate in duplicate_header_text:
            assert duplicate not in content, f"{duplicate} still present in {path}"



def test_ui_configuration_manager_removed():
    repo_root = Path(__file__).resolve().parents[1]
    shell_html = (repo_root / "src" / "ui" / "index.html").read_text()
    shell_js = (repo_root / "src" / "ui" / "index.js").read_text()

    removed_terms = [
        "UI Configuration",
        "UI Configuration Manager",
        "ui-config",
        "uiconfig",
        "fetchAndApplyUIConfiguration",
        "setupUIConfigManager",
        "/api/v1/ui/config",
    ]
    for term in removed_terms:
        assert term not in shell_html
        assert term not in shell_js



def test_src_runtime_code_has_no_external_weblinks():
    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / "src"
    forbidden = ["http://", "https://", "fonts.googleapis", "fonts.gstatic", "cdn.", "unpkg", "jsdelivr"]

    checked_files = [
        path
        for path in src_root.rglob("*")
        if path.is_file() and path.suffix in {".html", ".js", ".css", ".py"}
    ]
    assert checked_files

    for path in checked_files:
        content = path.read_text(errors="ignore")
        for term in forbidden:
            assert term not in content, f"{term} found in {path}"
