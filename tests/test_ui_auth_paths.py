from pathlib import Path


def test_micro_frontends_use_same_origin_api_paths():
    """Embedded UIs must not call a hardcoded host that loses the active login origin."""
    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / "AIP" / "src"

    checked_files = list(src_root.rglob("ui/index.html"))
    checked_files.append(src_root / "shared" / "create_sub_uis.py")

    assert checked_files
    for path in checked_files:
        content = path.read_text()
        assert "http://localhost:8000/api/v1" not in content, str(path)
