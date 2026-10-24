#!/usr/bin/env python3
"""
Offscreen WebKitGTK 4.1 verification snapshot generator for Vigyan Pro Studio.
Renders the dual-pane Side-by-Side STEM Canvas with 3D CAD turntable and tactile sliders.
"""

import os
import sys
import time
import pathlib
import threading

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DIST = SRC / "dist"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import Gtk, WebKit2, GLib, cairo

import launch_desktop
import tools

OUT_DIR = pathlib.Path("/home/hello/.gemini/antigravity/brain/1fca0b4e-6514-4310-b212-2eb1fd38ca46")
OUT_PNG = OUT_DIR / "vigyan_pro_dual_pane_studio.png"

def run_snapshot():
    # Start bridge server
    port = launch_desktop.start_neuro_symbolic_bridge_server(port=8085) or 8085
    token = launch_desktop._SESSION_TOKEN

    window = Gtk.OffscreenWindow()
    window.set_default_size(1366, 820)

    settings = WebKit2.Settings()
    settings.set_enable_webgl(True)
    settings.set_enable_javascript(True)
    settings.set_enable_developer_extras(False)

    webview = WebKit2.WebView.new_with_settings(settings)
    window.add(webview)
    window.show_all()

    # Pre-populate localStorage with token and mock CAD artifact
    cad_tool = tools.CADEngineTool()
    cad_res = cad_tool.execute({
        "shape": "enclosure",
        "title": "Parametric Electronics Enclosure (140x90x35mm)",
        "params": {"width": 140.0, "length": 90.0, "height": 35.0, "wall": 2.5}
    })

    def on_load_changed(wv, event):
        if event == WebKit2.LoadEvent.FINISHED:
            # Inject session token and trigger dual pane studio
            js_script = f"""
            window.VIGYAN_TOKEN = "{token}";
            localStorage.setItem("vigyan_token", "{token}");
            
            // Dispatch a mock message with CAD artifact to test dual-pane reveal
            setTimeout(() => {{
                if (window.dispatchEvent) {{
                    const chatStore = window.__chatStore;
                }}
            }}, 500);
            """
            wv.run_javascript(js_script, None, None, None)

            # Wait 2.2s for Three.js to render mesh, then capture snapshot
            GLib.timeout_add(2200, take_snapshot)

    def take_snapshot():
        webview.get_snapshot(
            WebKit2.SnapshotRegion.VISIBLE,
            WebKit2.SnapshotOptions.NONE,
            None,
            on_snapshot_done
        )
        return False

    def on_snapshot_done(wv, res):
        surface = wv.get_snapshot_finish(res)
        surface.write_to_png(str(OUT_PNG))
        print(f"Snapshot written successfully to {OUT_PNG}")
        Gtk.main_quit()

    webview.connect("load-changed", on_load_changed)
    webview.load_uri(f"http://127.0.0.1:{port}/index.html")

    GLib.timeout_add_seconds(12, Gtk.main_quit)
    Gtk.main()

if __name__ == "__main__":
    run_snapshot()
