#!/usr/bin/env python3
"""
Vigyan Pro Sovereign Studio - Native Desktop WebKitGTK Application
Pitch-Black Obsidian STEM Studio with LaTeX, Native Plots, and Ollama Auto-Connect.
Zero Browser Chrome. 100% Native Desktop Window.
"""

import sys
import os
import signal
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import Gtk, WebKit2, Gdk, GdkPixbuf, GLib

def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Wayland / XDG application identity mapping
    GLib.set_prgname("vigyan-pro")
    GLib.set_application_name("Vigyan Pro")

    win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    win.set_title("Vigyan Pro — Sovereign Studio")
    win.set_wmclass("vigyan-pro", "vigyan-pro")
    win.set_role("vigyan-pro")
    win.set_default_size(1340, 740)
    win.set_position(Gtk.WindowPosition.CENTER)

    # Dark background
    win.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 1))

    # Icon resolution
    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_candidates = [
        os.path.join(base_dir, "..", "assets", "micro_logo_v.png"),
        os.path.join(base_dir, "assets", "micro_logo_v.png"),
        "/opt/vigyan-pro/assets/micro_logo_v.png",
        "/usr/share/icons/hicolor/256x256/apps/vigyan-pro.png",
        os.path.expanduser("~/.local/share/icons/hicolor/256x256/apps/vigyan-pro.png"),
        os.path.expanduser("~/.vigyan/build/favicon.png")
    ]
    icon_path = next((p for p in icon_candidates if os.path.exists(p)), None)
    if icon_path:
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon_path)
            win.set_icon(pixbuf)
            Gtk.Window.set_default_icon(pixbuf)
            win.set_icon_name("vigyan-pro")
        except Exception:
            pass

    # WebKit Settings
    settings = WebKit2.Settings()
    settings.set_enable_javascript(True)
    settings.set_enable_webgl(True)
    settings.set_enable_write_console_messages_to_stdout(True)
    settings.set_allow_file_access_from_file_urls(True)
    settings.set_allow_universal_access_from_file_urls(True)

    # WebKit View
    webview = WebKit2.WebView.new_with_settings(settings)
    webview.set_background_color(Gdk.RGBA(0, 0, 0, 1))

    # Dynamic index.html discovery
    index_candidates = [
        os.path.join(base_dir, "index.html"),
        "/opt/vigyan-pro/src/index.html",
        os.path.expanduser("~/.vigyan/desktop/index.html")
    ]
    index_path = next((p for p in index_candidates if os.path.exists(p)), index_candidates[0])
    webview.load_uri(f"file://{os.path.abspath(index_path)}")

    win.add(webview)
    win.connect("destroy", Gtk.main_quit)

    win.show_all()
    win.present()
    Gtk.main()

if __name__ == "__main__":
    main()
