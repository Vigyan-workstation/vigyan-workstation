#!/usr/bin/env python3
"""
Vigyan Pro Sovereign Studio - Native macOS Desktop Launcher
Utilizes Apple Cocoa WKWebView on macOS (Intel and Apple Silicon M1/M2/M3/M4)
with native window vibrancy, pitch-black obsidian theme, and hardware-accelerated WebGL.
"""

import sys
import os
import subprocess

def launch_mac():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(base_dir, "index.html")

    # 1. Try pywebview with Cocoa WKWebView
    try:
        import webview
        window = webview.create_window(
            title="Vigyan Pro",
            url=f"file://{os.path.abspath(index_path)}",
            width=1340,
            height=760,
            resizable=True,
            background_color='#000000',
            easy_drag=False
        )
        webview.start(gui='cocoa', debug=False)
        return True
    except ImportError:
        pass
    except Exception as e:
        print(f"pywebview failed: {e}")

    # 2. Native macOS AppleScript WKWebView or Safari App Mode
    file_url = f"file://{os.path.abspath(index_path)}"
    
    # Try Google Chrome / Chromium app mode if installed on macOS
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
            f"--app={file_url}",
            "--window-size=1340,760",
            "--force-dark-mode"
        ]
        subprocess.Popen(cmd)
        return True

    # 3. Safari open fallback
    subprocess.Popen(["open", file_url])
    return True

if __name__ == "__main__":
    launch_mac()
