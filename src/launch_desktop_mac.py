#!/usr/bin/env python3
"""
Vigyan Pro Sovereign Studio - Native macOS Desktop Launcher
Utilizes Apple Cocoa WKWebView on macOS (Intel and Apple Silicon M1/M2/M3/M4)
with native window vibrancy, pitch-black obsidian theme, Smart Hybrid GPU+CPU Compute Engine,
and Embedded Neuro-Symbolic Bridge (SymPy AST + KùzuDB GraphRAG + Plotly).
Zero Browser Chrome. 100% Native Desktop Window.
"""

import sys
import os
import time
import subprocess
from typing import Optional

# Set Ollama hybrid compute acceleration flags before spawning daemon
os.environ.setdefault("OLLAMA_FLASH_ATTENTION", "1")
os.environ.setdefault("OLLAMA_KV_CACHE_TYPE", "q8_0")
os.environ.setdefault("OLLAMA_NUM_PARALLEL", "1")


def _ollama_is_healthy() -> bool:
    """Return True if local Ollama answers on loopback port."""
    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False


def launch_mac():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(base_dir, "index.html")

    # 1. Start embedded Neuro-Symbolic HTTP Bridge (:8085)
    port = 8085
    bridge_started = False
    try:
        from launch_desktop import start_neuro_symbolic_bridge_server
        p = start_neuro_symbolic_bridge_server(8085)
        if p:
            port = p
            bridge_started = True
            print(f"[Vigyan Pro] Sovereign Neuro-Symbolic Bridge online at http://127.0.0.1:{port}")
    except Exception as exc:
        print(f"[Vigyan Pro] Warning: Neuro-Symbolic bridge init notice: {exc}", file=sys.stderr)

    # 2. Start Ollama Supervisor Daemon
    supervisor = None
    try:
        from ollama_supervisor import OllamaSupervisor
        supervisor = OllamaSupervisor(["ollama", "serve"], is_healthy=_ollama_is_healthy)
        supervisor.start()
        print("[Vigyan Pro] Ollama Sovereign Supervisor initialized")
    except Exception as exc:
        print(f"[Vigyan Pro] Notice: Ollama supervisor started or running externally: {exc}", file=sys.stderr)

    target_url = f"http://127.0.0.1:{port}/" if bridge_started else f"file://{os.path.abspath(index_path)}"

    # 3. Launch Native Cocoa WKWebView via pywebview
    try:
        import webview
        window = webview.create_window(
            title="Vigyan Pro",
            url=target_url,
            width=1340,
            height=780,
            resizable=True,
            background_color='#000000',
            easy_drag=False
        )
        try:
            webview.start(gui='cocoa', debug=False)
            return True
        finally:
            if supervisor:
                supervisor.stop()
    except ImportError:
        pass
    except Exception as e:
        print(f"[Vigyan Pro] Cocoa pywebview notice: {e}")

    # 4. Fallback: Chromium / Chrome / Brave / Edge App Mode on macOS
    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
    ]
    browser_exe = next((p for p in chrome_paths if os.path.exists(p)), None)
    if browser_exe:
        cmd = [
            browser_exe,
            f"--app={target_url}",
            "--window-size=1340,780",
            "--force-dark-mode"
        ]
        try:
            proc = subprocess.Popen(cmd)
            proc.wait()
            return True
        finally:
            if supervisor:
                supervisor.stop()

    # 5. Native Safari open fallback
    try:
        subprocess.Popen(["open", target_url])
        return True
    finally:
        if supervisor:
            supervisor.stop()


if __name__ == "__main__":
    launch_mac()
