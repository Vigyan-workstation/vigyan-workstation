#!/usr/bin/env python3
"""
Offscreen WebKitGTK 4.1 verification snapshot generator for Unified Vigyan Pro Workstation.
Renders and captures:
- Dual-pane 52%/48% Split Workstation
- Chat stream with:
  1. 6-DoF Robotics Kinematics Card
  2. WaveDrom Digital Bus Timing Diagram
  3. Silicon EDA RTL Synthesis Metrics
  4. Luxury Human-in-the-Loop Terminal Security Gate Card
- Side-by-Side Studio Canvas with 6-DoF Robotics Kinematics skeleton, reach indicator, and tactile sliders
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
OUT_PNG = OUT_DIR / "vigyan_pro_unified_workstation_verified.png"

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

    # Pre-generate sample data
    rob_tool = tools.RoboticsEngineTool()
    rob_res = rob_tool.execute({
        "arm_type": "6dof_industrial",
        "joint_angles_deg": [25, 40, -45, 0, 20, 0]
    })

    wave_tool = tools.WaveEngineTool()
    wave_res = wave_tool.execute({
        "protocol": "spi_master",
        "title": "SPI Bus 4-Byte Read Transaction"
    })

    eda_tool = tools.SiliconEDATool()
    eda_res = eda_tool.execute({
        "code": "module spi_controller(input clk, input rst_n, input [7:0] tx_data, output reg miso); always @(posedge clk) begin miso <= tx_data[7]; end endmodule",
        "target_clock_mhz": 100
    })

    def on_load_changed(wv, event):
        if event == WebKit2.LoadEvent.FINISHED:
            rob_json = json.dumps(rob_res)
            wave_json = json.dumps(wave_res)
            eda_json = json.dumps(eda_res)

            js_script = f"""
            window.VIGYAN_TOKEN = "{token}";
            localStorage.setItem("vigyan_token", "{token}");

            const robData = {rob_json};
            const waveData = {wave_json};
            const edaData = {eda_json};

            const mockMessages = [
                {{
                    id: "u1",
                    role: "user",
                    content: "Compute 6-DoF arm forward kinematics, SPI timing, and analyze the Verilog SPI controller.",
                    thinking: "",
                    thinkingDone: true,
                    streaming: false
                }},
                {{
                    id: "a1",
                    role: "assistant",
                    content: "Here is the unified analysis across kinematics, digital bus timing, and silicon RTL synthesis.",
                    thinking: "Solved Denavit-Hartenberg transformation matrices, analyzed timing parameters, and synthesized RTL cells.",
                    thinkingDone: true,
                    streaming: false,
                    toolResults: [
                        robData,
                        waveData,
                        edaData,
                        {{
                            status: "requires_approval",
                            command: "apt install -y yosys arachne-pnr",
                            risk: "high",
                            reason: "Installation of FPGA synthesis packages modifies root filesystem.",
                            cwd: "/home/hello/workspace"
                        }}
                    ]
                }}
            ];

            const mockStudio = {{
                id: "art_rob_1",
                tool: "robotics_kinematics",
                render_type: "robotics",
                title: "6-DoF Industrial Arm (UR5/Puma DH Kinematics)",
                arm_type: robData.arm_type,
                joint_angles_deg: robData.joint_angles_deg,
                end_effector: robData.end_effector,
                reach_mm: robData.reach_mm,
                joint_chain: robData.joint_chain,
                metrics: robData.metrics
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
        print(f"Unified snapshot written successfully to {OUT_PNG}")
        Gtk.main_quit()

    webview.connect("load-changed", on_load_changed)
    webview.load_uri(f"http://127.0.0.1:{port}/")

    GLib.timeout_add_seconds(14, Gtk.main_quit)
    Gtk.main()

if __name__ == "__main__":
    run_snapshot()
