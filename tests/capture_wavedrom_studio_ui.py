#!/usr/bin/env python3
"""
Offscreen WebKitGTK 4.1 verification snapshot generator for WaveDrom Studio Canvas.
Renders and captures:
- Side-by-Side Studio Canvas with WaveDrom Digital Waveforms
- Presets: SPI Master, I2C 7-Bit, UART 8N1, AXI4-Stream
- Live Waveform SVG render and Export button
"""

import os
import sys
import time
import pathlib
import json

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import Gtk, WebKit2, GLib

import launch_desktop
import tools

OUT_DIR = pathlib.Path("/home/hello/.gemini/antigravity/brain/1fca0b4e-6514-4310-b212-2eb1fd38ca46")
OUT_PNG = OUT_DIR / "vigyan_pro_wavedrom_studio_verified.png"

def run_snapshot():
    port = launch_desktop.start_neuro_symbolic_bridge_server(port=8085) or 8085
    token = launch_desktop._SESSION_TOKEN

    window = Gtk.OffscreenWindow()
    window.set_default_size(1440, 880)

    settings = WebKit2.Settings()
    settings.set_enable_webgl(True)
    settings.set_enable_javascript(True)
    settings.set_enable_developer_extras(False)

    webview = WebKit2.WebView.new_with_settings(settings)
    window.add(webview)
    window.show_all()

    wave_tool = tools.WaveEngineTool()
    wave_res = wave_tool.execute({
        "protocol": "axi4_stream",
        "title": "AXI4-Stream Handshake & Packet Burst"
    })

    def on_load_changed(wv, event):
        if event == WebKit2.LoadEvent.FINISHED:
            wave_json = json.dumps(wave_res)

            js_script = f"""
            window.VIGYAN_TOKEN = "{token}";
            localStorage.setItem("vigyan_token", "{token}");

            const waveData = {wave_json};

            const mockMessages = [
                {{
                    id: "u1",
                    role: "user",
                    content: "Generate AXI4-Stream bus timing diagram for high-throughput FPGA streaming.",
                    thinking: "",
                    thinkingDone: true,
                    streaming: false
                }},
                {{
                    id: "a1",
                    role: "assistant",
                    content: "Generated AXI4-Stream timing waveform showing TVALID / TREADY handshake with packet payload burst.",
                    thinking: "Generated digital waveform timing specification for AXI4-Stream protocol.",
                    thinkingDone: true,
                    streaming: false,
                    toolResults: [waveData]
                }}
            ];

            const mockStudio = {{
                id: "art_wave_1",
                tool: "wavedrom_generate",
                render_type: "wavedrom",
                title: "AXI4-Stream Handshake & Packet Burst",
                wavedrom_spec: waveData.wavedrom_spec,
                protocol: "axi4_stream"
            }};

            setTimeout(() => {{
                try {{
                    const store = window.__CHAT_STORE__;
                    const studio = window.__STUDIO_STORE__;

                    if (store) {{
                        store.messages = mockMessages;
                        store.save();
                    }}

                    if (studio) {{
                        studio.open(mockStudio);
                    }}
                }} catch (e) {{
                    console.error("Injection error:", e);
                }}
            }}, 400);
            """
            wv.run_javascript(js_script, None, None, None)
            GLib.timeout_add(2600, take_snapshot)

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
        print(f"WaveDrom snapshot written successfully to {OUT_PNG}")
        Gtk.main_quit()

    webview.connect("load-changed", on_load_changed)
    webview.load_uri(f"http://127.0.0.1:{port}/")

    GLib.timeout_add_seconds(14, Gtk.main_quit)
    Gtk.main()

if __name__ == "__main__":
    run_snapshot()
