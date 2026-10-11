#!/usr/bin/env python3
"""
Vigyan Pro Sovereign Studio - Native Windows Desktop Launcher
Utilizes Microsoft Edge WebView2 on Windows 10/11 with zero browser chrome,
pitch-black obsidian theme, and hardware-accelerated WebGL.
"""

import sys
import os
import subprocess

def launch_webview2():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(base_dir, "index.html")
    icon_path = os.path.join(base_dir, "..", "assets", "micro_logo_v.ico")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(base_dir, "assets", "micro_logo_v.png")

    # 1. Try pywebview with edgechromium (WebView2)
    try:
        import webview
        window = webview.create_window(
            title="Vigyan Pro",
            url=f"file:///{index_path.replace(os.sep, '/')}",
            width=1340,
            height=760,
            resizable=True,
            background_color='#000000',
            easy_drag=False
        )
        webview.start(gui='edgechromium', debug=False)
        return True
    except ImportError:
        pass
    except Exception as e:
        print(f"pywebview failed: {e}")

    # 2. Native Microsoft Edge App Mode Fallback (Installed on all Windows 10/11)
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe")
    ]
    edge_exe = next((p for p in edge_paths if os.path.exists(p)), "msedge.exe")
    
    file_url = f"file:///{index_path.replace(os.sep, '/')}"
    cmd = [
        edge_exe,
        f"--app={file_url}",
        "--window-size=1340,760",
        "--enable-features=OverlayScrollbar",
        "--force-dark-mode"
    ]
    try:
        proc = subprocess.Popen(cmd)
        proc.wait()
        return True
    except Exception as e:
        print(f"Failed to launch Edge app mode: {e}")
        import webbrowser
        webbrowser.open(file_url)
        return True

def _ollama_is_healthy() -> bool:
    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False

def main():
    try:
        from ollama_supervisor import OllamaSupervisor
        supervisor = OllamaSupervisor(["ollama", "serve"], is_healthy=_ollama_is_healthy)
        try:
            supervisor.start()
        except Exception as exc:
            print(f"[WARN] could not start ollama on windows: {exc}", file=sys.stderr)
        try:
            launch_webview2()
        finally:
            supervisor.stop()
    except ImportError:
        launch_webview2()

if __name__ == "__main__":
    main()

