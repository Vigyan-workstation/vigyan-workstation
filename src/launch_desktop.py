#!/usr/bin/env python3
"""
Vigyan Pro Sovereign Studio - Native Desktop WebKitGTK Application
Pitch-Black Obsidian STEM Studio with LaTeX, Native Plots, and Ollama Auto-Connect.
Zero Browser Chrome. 100% Native Desktop Window.
"""

import sys
import os
import signal
import subprocess
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import Gtk, WebKit2, Gdk, GdkPixbuf, GLib

from ollama_supervisor import OllamaSupervisor

def _ollama_is_healthy() -> bool:
    """Return True if a local Ollama answers on its loopback port."""
    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False


OLLAMA = OllamaSupervisor(["ollama", "serve"], is_healthy=_ollama_is_healthy)


def ensure_ollama_daemon() -> None:
    """Make sure a local Ollama is running; start one we own if it is not."""
    try:
        OLLAMA.start()
    except OSError as exc:  # e.g. ollama is not installed
        print(f"[WARN] could not start ollama: {exc}", file=sys.stderr)


def _watch_ollama() -> bool:
    """GLib timer callback: restart a crashed Ollama child. True keeps the timer."""
    OLLAMA.check()
    return True


def main():
    # Exit through the GTK main loop so the cleanup after Gtk.main() always runs.
    try:
        from gi.repository import GLibUnix
        GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, Gtk.main_quit)
        GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, Gtk.main_quit)
    except Exception:
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, Gtk.main_quit)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, Gtk.main_quit)

    # Wayland / XDG application identity mapping
    GLib.set_prgname("vigyan-pro")
    GLib.set_application_name("Vigyan Pro")

    # Proactively check / ensure Ollama background service
    ensure_ollama_daemon()

    win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    win.set_title("Vigyan Pro")
    win.set_role("vigyan-pro")
    win.set_default_size(1340, 740)
    win.set_position(Gtk.WindowPosition.CENTER)

    # Modern CSS Provider for pitch-black background (replaces deprecated override_background_color)
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(b"window { background-color: #000000; }")
    win.get_style_context().add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

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

    # WebKit Settings & GPU Acceleration
    settings = WebKit2.Settings()
    settings.set_enable_javascript(True)
    settings.set_enable_webgl(True)
    settings.set_enable_write_console_messages_to_stdout(True)
    settings.set_allow_file_access_from_file_urls(True)
    settings.set_allow_universal_access_from_file_urls(True)
    settings.set_enable_smooth_scrolling(True)
    try:
        settings.set_hardware_acceleration_policy(WebKit2.HardwareAccelerationPolicy.ALWAYS)
    except Exception:
        pass

    # WebKit View
    webview = WebKit2.WebView.new_with_settings(settings)
    webview.set_background_color(Gdk.RGBA(0, 0, 0, 1))

    # Enterprise Navigation Policy: Prevent webview URL hijacking / unauthorized redirection
    def on_decide_policy(view, decision, decision_type):
        if decision_type == WebKit2.PolicyDecisionType.NAVIGATION_ACTION:
            action = decision.get_navigation_action()
            req = action.get_request()
            uri = req.get_uri() if req else ""
            if uri.startswith("file://") or uri.startswith("about:blank"):
                return False
            # Ignore arbitrary web requests in workstation frame and safely open externally if needed
            decision.ignore()
            try:
                import webbrowser
                webbrowser.open(uri)
            except Exception:
                pass
            return True
        return False

    webview.connect("decide-policy", on_decide_policy)

    # Dynamic index.html discovery
    index_candidates = [
        os.path.join(base_dir, "index.html"),
        "/opt/vigyan-pro/src/index.html",
        os.path.expanduser("~/.vigyan/desktop/index.html")
    ]
    index_path = next((p for p in index_candidates if os.path.exists(p)), index_candidates[0])
    webview.load_uri(f"file://{os.path.abspath(index_path)}")

    # Keyboard shortcuts: F11 Fullscreen, Ctrl+R Reload
    def on_key_press(widget, event):
        keyval = event.keyval
        state = event.state
        if keyval == Gdk.KEY_F11:
            if win.get_window().get_state() & Gdk.WindowState.FULLSCREEN:
                win.unfullscreen()
            else:
                win.fullscreen()
            return True
        elif keyval in (Gdk.KEY_r, Gdk.KEY_R) and (state & Gdk.ModifierType.CONTROL_MASK):
            webview.reload()
            return True
        return False

    win.connect("key-press-event", on_key_press)
    win.add(webview)
    win.connect("destroy", Gtk.main_quit)

    snapshot_path = None
    if "--snapshot" in sys.argv:
        idx = sys.argv.index("--snapshot")
        if idx + 1 < len(sys.argv):
            snapshot_path = sys.argv[idx + 1]

    if snapshot_path:
        def on_snapshot_done(view, res, target):
            try:
                surface = view.get_snapshot_finish(res)
                surface.write_to_png(target)
                print(f"[OK] Snapshot saved to {target}")
            except Exception as e:
                print(f"[ERR] Snapshot failed: {e}")
            Gtk.main_quit()

        def trigger_snapshot():
            webview.get_snapshot(
                WebKit2.SnapshotRegion.FULL_DOCUMENT,
                WebKit2.SnapshotOptions.NONE,
                None,
                on_snapshot_done,
                snapshot_path
            )
            return False

        def on_load_changed(view, event):
            if event == WebKit2.LoadEvent.FINISHED:
                GLib.timeout_add(1500, trigger_snapshot)

        webview.connect("load-changed", on_load_changed)

    win.show_all()
    win.present()
    GLib.timeout_add_seconds(5, _watch_ollama)
    try:
        Gtk.main()
    finally:
        OLLAMA.stop()

if __name__ == "__main__":
    main()
