import json
import pathlib
import re
import subprocess
import sys
import unittest
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import launch_desktop
import launch_desktop_win
from ollama_supervisor import OllamaSupervisor


class TestHybridComputeAndNeuroSymbolicStudio(unittest.TestCase):
    def test_ollama_supervisor_flash_attention_and_kv_env(self):
        sup = OllamaSupervisor(
            command=["echo", "serve"],
            is_healthy=lambda: True,
            extra_env={"CUSTOM_VAR": "42"},
        )
        self.assertEqual(sup._extra_env.get("OLLAMA_FLASH_ATTENTION"), "1")
        self.assertEqual(sup._extra_env.get("OLLAMA_KV_CACHE_TYPE"), "q8_0")
        self.assertEqual(sup._extra_env.get("OLLAMA_NUM_PARALLEL"), "1")
        self.assertEqual(sup._extra_env.get("CUSTOM_VAR"), "42")

    def test_compute_hybrid_allocation_all_modes_and_edge_cases(self):
        hw_apu = {"physical_cores": 4, "logical_cores": 8, "ram_total_gb": 8.0}
        gpu_apu = {
            "has_gpu": True,
            "is_apu": True,
            "vram_total_mb": 512.0,
            "gtt_total_mb": 3564.0,
        }
        power_ac = {"is_laptop": True, "on_battery": False, "battery_pct": 95}
        power_low_bat = {"is_laptop": True, "on_battery": True, "battery_pct": 15}

        # 1. Auto mode with APU + healthy RAM headroom on AC
        res_auto = launch_desktop.compute_hybrid_allocation(
            mode="auto",
            hw=hw_apu,
            gpu_metrics=gpu_apu,
            power=power_ac,
            ram_avail_gb=3.6,
        )
        self.assertEqual(res_auto["mode"], "auto")
        self.assertEqual(res_auto["num_gpu"], 20)
        self.assertEqual(res_auto["num_thread"], 4)

        # 2. Max GPU mode on 24GB RAM desktop dGPU
        res_max = launch_desktop.compute_hybrid_allocation(
            mode="max_gpu",
            hw={"physical_cores": 8, "logical_cores": 16, "ram_total_gb": 24.0},
            gpu_metrics={"has_gpu": True, "is_apu": False, "vram_total_mb": 12288.0, "gtt_total_mb": 0.0},
            power={"is_laptop": False, "on_battery": False, "battery_pct": 100},
            ram_avail_gb=18.0,
        )
        self.assertEqual(res_max["num_gpu"], 99)
        self.assertEqual(res_max["num_ctx"], 16384)

        # 3. Balanced GPU+CPU mode
        res_bal = launch_desktop.compute_hybrid_allocation(
            mode="balanced",
            hw=hw_apu,
            gpu_metrics=gpu_apu,
            power=power_ac,
            ram_avail_gb=4.0,
        )
        self.assertEqual(res_bal["num_gpu"], 16)
        self.assertEqual(res_bal["num_thread"], 4)

        # 4. CPU Eco mode forces num_gpu=0 even when GPU is present
        res_eco = launch_desktop.compute_hybrid_allocation(
            mode="cpu_eco",
            hw=hw_apu,
            gpu_metrics=gpu_apu,
            power=power_ac,
            ram_avail_gb=4.0,
        )
        self.assertEqual(res_eco["num_gpu"], 0)

        # 5. Edge case: Auto mode with low battery (<20%) drops to CPU battery saver
        res_bat = launch_desktop.compute_hybrid_allocation(
            mode="auto",
            hw=hw_apu,
            gpu_metrics=gpu_apu,
            power=power_low_bat,
            ram_avail_gb=4.0,
        )
        self.assertEqual(res_bat["num_gpu"], 0)

        # 6. Edge case: Unknown mode falls back cleanly to auto, no GPU available
        res_fallback = launch_desktop.compute_hybrid_allocation(
            mode="invalid_mode_xyz",
            hw={"physical_cores": 4, "logical_cores": 4, "ram_total_gb": 4.0},
            gpu_metrics={"has_gpu": False, "is_apu": False, "vram_total_mb": 0.0, "gtt_total_mb": 0.0},
            power=power_ac,
            ram_avail_gb=1.5,
        )
        self.assertEqual(res_fallback["mode"], "auto")
        self.assertEqual(res_fallback["num_gpu"], 0)

    def test_get_system_telemetry_live_host(self):
        tel = launch_desktop.get_system_telemetry("auto")
        self.assertIn("cpu_percent", tel)
        self.assertIn("ram_percent", tel)
        self.assertIn("ollama_options", tel)
        self.assertIn("strategy_label", tel)
        self.assertGreaterEqual(tel["cpu_cores_physical"], 1)

    def test_windows_launcher_telemetry_fallback(self):
        win_tel = launch_desktop_win.get_windows_telemetry("balanced")
        self.assertEqual(win_tel["compute_mode"], "balanced")
        self.assertIn("ollama_options", win_tel)
        self.assertIn("num_gpu", win_tel["ollama_options"])

    def test_neuro_symbolic_enrichment_and_edge_cases(self):
        # Empty query edge case
        empty_res = launch_desktop.enrich_stem_query("")
        self.assertFalse(empty_res["sympy_verified"])
        self.assertEqual(empty_res["axioms"], [])

        # Semiconductor + Physics axiom retrieval
        semi_res = launch_desktop.enrich_stem_query("/semiconductor MOSFET band bending and Schrodinger wave")
        self.assertGreaterEqual(len(semi_res["axioms"]), 1)
        self.assertIn("KùzuDB", semi_res["enriched_system_suffix"])

        # Algebraic equation SymPy verification
        alg_res = launch_desktop.enrich_stem_query("Solve x^2 - 5*x + 6 = 0")
        if launch_desktop._SYMPY_ENGINE is not None:
            self.assertTrue(alg_res["sympy_verified"])
            self.assertIn("2", alg_res["sympy_result"])
            self.assertIn("3", alg_res["sympy_result"])

    def test_embedded_neuro_symbolic_http_server(self):
        port = 18086
        srv = launch_desktop.start_neuro_symbolic_bridge_server(port=port)
        self.assertIsNotNone(srv)

        # Unauthenticated request must return 403 Forbidden
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/telemetry", timeout=3)
        self.assertEqual(cm.exception.code, 403)

        # Authenticated request with session token succeeds
        headers = {"X-Vigyan-Token": launch_desktop._SESSION_TOKEN}
        req_tel = urllib.request.Request(f"http://127.0.0.1:{port}/api/telemetry", headers=headers)
        with urllib.request.urlopen(req_tel, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("ollama_options", data)

        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/compute_mode",
            data=json.dumps({"mode": "balanced"}).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-Vigyan-Token": launch_desktop._SESSION_TOKEN},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["compute_mode"], "balanced")

        req_enrich = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/enrich",
            data=json.dumps({"query": "/material fcc bragg diffraction"}).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-Vigyan-Token": launch_desktop._SESSION_TOKEN},
            method="POST",
        )
        with urllib.request.urlopen(req_enrich, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(len(data["axioms"]) >= 1)

    def test_index_html_eight_domains_modals_and_js_syntax(self):
        html_path = SRC / "index.html"
        html = html_path.read_text(encoding="utf-8")

        for fn in [
            "initInChatCAD",
            "initInChatSemi",
            "initInChatPlot",
            "initInChatCircuit",
            "initInChatSim",
            "initInChatMaterial",
            "initInChatBiology",
            "initInChatMathVisual",
            "initInChatMedical",
            "setHybridComputeMode",
            "onBackendTypeChange",
        ]:
            self.assertIn(fn, html, f"Missing required function {fn} in src/index.html")
        for removed_modal in ["openStemTaskHub", "openLatexRefModal", "openExportPdfModal"]:
            self.assertNotIn(removed_modal, html, f"Removed modal function {removed_modal} should not be in src/index.html")

        scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
        self.assertGreaterEqual(len(scripts), 1)
        tmp_js = pathlib.Path("/tmp/test_vigyan_syntax.js")
        tmp_js.write_text(scripts[-1], encoding="utf-8")
        proc = subprocess.run(["node", "--check", str(tmp_js)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"JS syntax check failed: {proc.stderr}")

    def test_enterprise_settings_rows_and_functions(self):
        html_path = SRC / "index.html"
        html = html_path.read_text(encoding="utf-8")

        # Verify all newly implemented executive settings functions exist
        for fn in [
            "setContextLength",
            "setGovernorThreshold",
            "toggleTelemetryHUD",
            "setCodeFont",
            "toggleSmartScroll",
            "toggleHaptics",
            "exportAllChats",
            "clearAllChatHistory",
            "purgeModelCache"
        ]:
            self.assertIn(fn, html, f"Missing executive settings function {fn} in index.html")

        # Verify essential DOM elements exist
        for dom_id in [
            "header-hud-telemetry",
            "hud-ram-text",
            "hud-gpu-text",
            "setting-ctx-select",
            "setting-font-select",
            "toggle-hud-switch",
            "toggle-scroll-switch",
            "toggle-haptics-switch",
            "gov-btn-80",
            "gov-btn-85",
            "gov-btn-90"
        ]:
            self.assertIn(f'id="{dom_id}"', html, f"Missing element with id '{dom_id}' in index.html")

        # Verify header and nav are properly closed before main
        self.assertIn("</nav>", html)
        self.assertIn("</header>", html)
        nav_close = html.find("</nav>")
        header_close = html.find("</header>")
        main_open = html.find('<main class="app-main">')
        self.assertGreater(header_close, nav_close, "Header must close after nav")
        self.assertGreater(main_open, header_close, "<main> must start AFTER </header> to prevent layout collapse")

        # Verify legacy quad-master model is absent from model selection
        self.assertNotIn("vigyan:7b-quad-master", html.replace("vigyan:7b-quad-master", "", 1))  # only 1 occurrence in sanitizer allowed


if __name__ == "__main__":
    unittest.main()
