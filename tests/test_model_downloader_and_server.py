"""
Test Suite for Vigyan Pro Sovereign Model Downloader, Catalog, and Cross-Platform HTTP Bridge.
"""

import os
import sys
import json
import pytest
import tempfile
import urllib.request
import threading
import time

# Ensure src/ is on path
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from launch_desktop import (
    MODELS_CATALOG,
    ModelDownloadManager,
    grep_workspace_files,
    start_neuro_symbolic_bridge_server,
    _SESSION_TOKEN,
)


def test_models_catalog_integrity():
    """Verify that models catalog entries contain valid URLs, tags, and reasonable sizes."""
    assert "vigyan:1.5b" in MODELS_CATALOG
    assert len(MODELS_CATALOG) >= 1

    for tag, info in MODELS_CATALOG.items():
        assert info["tag"] == tag
        assert info["size_bytes"] > 1_000_000_000  # >= 1 GB
        assert info["hf_url"].startswith("https://huggingface.co/") or info["hf_url"].startswith("https://github.com/")
        assert info["dest_filename"].endswith(".gguf")
        assert "TEMPLATE" in f"TEMPLATE {info['template']}"
        assert len(info.get("stop", [])) > 0


def test_model_download_manager_lifecycle():
    """Test ModelDownloadManager status tracking and cancel lifecycle."""
    mgr = ModelDownloadManager()
    status = mgr.get_status()
    assert isinstance(status, dict)

    # Unknown tag error check
    res = mgr.start_download("non_existent_model:99b")
    assert res["success"] is False
    assert "Unknown model" in res["error"]

    # Valid tag status initialization
    initial = mgr.get_status("vigyan:1.5b")
    assert initial.get("status") in ("idle", "ready")

    # Cancel download on idle/ready tag
    cancelled = mgr.cancel_download("vigyan:1.5b")
    assert cancelled is False


def test_pure_python_grep_fallback(tmp_path):
    """Verify cross-platform pure-Python grep search handles queries accurately."""
    f1 = tmp_path / "circuit.py"
    f1.write_text("def solve_rc_filter(r, c):\n    return 1.0 / (2 * 3.14159 * r * c)\n", encoding="utf-8")

    f2 = tmp_path / "notes.txt"
    f2.write_text("Euler identity: e^(i*pi) + 1 = 0\nsolve_rc_filter is useful\n", encoding="utf-8")

    res = grep_workspace_files("solve_rc_filter", path=str(tmp_path))
    assert res["success"] is True
    assert len(res["matches"]) == 2
    files = [m["file"] for m in res["matches"]]
    assert any("circuit.py" in f for f in files)
    assert any("notes.txt" in f for f in files)


def test_http_bridge_static_serving_and_catalog():
    """Verify embedded HTTP server serves index.html, /api/models/catalog, and static assets."""
    port = start_neuro_symbolic_bridge_server(8089)
    assert port == 8089
    time.sleep(0.3)

    # 1. Test index.html static serving
    req_index = urllib.request.Request(f"http://127.0.0.1:{port}/")
    with urllib.request.urlopen(req_index, timeout=3.0) as resp:
        assert resp.status == 200
        assert "text/html" in resp.headers.get("Content-Type", "")
        content = resp.read().decode("utf-8")
        assert "Vigyan Pro" in content

    # 2. Test unauthenticated API endpoint returns 403 Forbidden
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/api/models/catalog", timeout=3.0)
        assert False, "Unauthenticated request should have failed with 403"
    except urllib.error.HTTPError as e:
        assert e.code == 403

    # 3. Test authenticated /api/models/catalog JSON endpoint
    auth_headers = {"X-Vigyan-Token": _SESSION_TOKEN}
    req_cat = urllib.request.Request(f"http://127.0.0.1:{port}/api/models/catalog", headers=auth_headers)
    with urllib.request.urlopen(req_cat, timeout=3.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "catalog" in data
        assert "vigyan:1.5b" in data["catalog"]
        assert "system_ram_gb" in data

    # 4. Test authenticated /api/models/download/status endpoint
    req_st = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/models/download/status?tag=vigyan:1.5b",
        headers=auth_headers
    )
    with urllib.request.urlopen(req_st, timeout=3.0) as resp:
        assert resp.status == 200
        st = json.loads(resp.read().decode("utf-8"))
        assert "status" in st
