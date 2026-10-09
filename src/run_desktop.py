#!/usr/bin/env python3
"""
Vigyan Pro Sovereign Studio - Universal Cross-Platform Entrypoint
Auto-detects host operating system (Linux, Windows, macOS) and executes
the optimized native desktop environment.
"""

import sys
import os
import subprocess

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    platform = sys.platform

    if platform.startswith("linux"):
        launcher = os.path.join(base_dir, "launch_desktop.py")
        cmd = [sys.executable, launcher] + sys.argv[1:]
    elif platform.startswith("win32") or platform.startswith("cygwin"):
        launcher = os.path.join(base_dir, "launch_desktop_win.py")
        cmd = [sys.executable, launcher] + sys.argv[1:]
    elif platform.startswith("darwin"):
        launcher = os.path.join(base_dir, "launch_desktop_mac.py")
        cmd = [sys.executable, launcher] + sys.argv[1:]
    else:
        # Generic fallback
        launcher = os.path.join(base_dir, "launch_desktop.py")
        cmd = [sys.executable, launcher] + sys.argv[1:]

    try:
        sys.exit(subprocess.call(cmd))
    except Exception as e:
        print(f"Error launching Vigyan Pro: {e}")
        # Final fallback: open browser
        import webbrowser
        index_path = os.path.join(base_dir, "index.html")
        webbrowser.open(f"file://{os.path.abspath(index_path)}")

if __name__ == "__main__":
    main()
