"""
Comprehensive Unit Tests for Vigyan Pro Desktop STEM Toolkits.
Strictly Permissive Open-Source Verification (Apache 2.0 / MIT / BSD-2 / ISC).
100% Offline, Air-Gapped Operation.
"""

import base64
import json
import math
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import tools
from tools.base import BaseTool
from tools.cad_engine import CADEngineTool
from tools.wave_engine import WaveEngineTool
from tools.pcb_engine import PCBEngineTool
from tools.silicon_eda import SiliconEDATool
from tools.robotics_engine import RoboticsEngineTool
import launch_desktop


class TestSTEMToolkits(unittest.TestCase):
    def test_tool_registry_discovery(self):
        registered = tools.get_all_tools()
        self.assertIn("cad_model_generate", registered)
        self.assertIn("wavedrom_generate", registered)
        self.assertIn("pcb_netlist_generate", registered)
        self.assertIn("verilog_analyze", registered)
        self.assertIn("robotics_kinematics", registered)

        # Verify prompt instructions contain all tools
        prompt = tools.get_tool_schemas_prompt()
        for name in registered.keys():
            self.assertIn(name, prompt)

    def test_cad_engine_parametric_enclosure(self):
        cad = CADEngineTool()
        args = {
            "shape": "enclosure",
            "title": "Electronics Project Box (120x80x35mm)",
            "params": {"width": 120, "length": 80, "height": 35, "wall": 2.5}
        }
        res = cad.execute(args)
        self.assertTrue(res["success"])
        self.assertEqual(res["render_type"], "threejs_cad")
        self.assertIn("positions", res["mesh"])
        self.assertIn("normals", res["mesh"])
        self.assertGreater(len(res["mesh"]["positions"]), 100)
        self.assertEqual(len(res["mesh"]["positions"]), len(res["mesh"]["normals"]))

        # Verify STL export
        stl_ascii = base64.b64decode(res["stl_base64"]).decode("utf-8")
        self.assertTrue(stl_ascii.startswith("solid enclosure"))
        self.assertTrue(stl_ascii.strip().endswith("endsolid enclosure"))
        self.assertIn("facet normal", stl_ascii)

        # Check metrics
        labels = [m["label"] for m in res["metrics"]]
        self.assertIn("Bounding Box", labels)
        self.assertIn("Enclosed Vol", labels)
        self.assertIn("Mesh Triangles", labels)

    def test_cad_engine_gear_and_bracket(self):
        cad = CADEngineTool()
        # Gear
        res_gear = cad.execute({"shape": "gear", "params": {"teeth": 16, "module": 2.0}})
        self.assertTrue(res_gear["success"])
        self.assertGreater(res_gear["mesh"]["triangle_count"], 50)

        # Bracket
        res_bracket = cad.execute({"shape": "bracket", "params": {"width": 50, "length": 50, "height": 30}})
        self.assertTrue(res_bracket["success"])
        self.assertGreater(res_bracket["mesh"]["triangle_count"], 20)

    def test_wave_engine_digital_buses(self):
        wave = WaveEngineTool()
        # SPI Master
        res_spi = wave.execute({"protocol": "spi_master"})
        self.assertTrue(res_spi["success"])
        self.assertEqual(res_spi["render_type"], "wavedrom")
        spec = res_spi["wavedrom_spec"]
        sig_names = [s["name"] for s in spec["signal"]]
        self.assertIn("CS_n", sig_names)
        self.assertIn("SCLK", sig_names)
        self.assertIn("MOSI", sig_names)

        # I2C Bus
        res_i2c = wave.execute({"protocol": "i2c_bus"})
        self.assertTrue(res_i2c["success"])
        i2c_names = [s["name"] for s in res_i2c["wavedrom_spec"]["signal"]]
        self.assertIn("SCL", i2c_names)
        self.assertIn("SDA", i2c_names)

    def test_pcb_netlist_engine_555_and_filter(self):
        pcb = PCBEngineTool()
        # 555 Astable
        res_555 = pcb.execute({"circuit_type": "555_timer", "params": {"r1": 10000, "r2": 47000, "c1": 1e-6}})
        self.assertTrue(res_555["success"])
        self.assertEqual(res_555["render_type"], "pcb_circuit")
        self.assertIn("NE555P", res_555["kicad_netlist"])
        self.assertIn("(export (version D)", res_555["kicad_netlist"])
        self.assertIn("* Vigyan SPICE: NE555 Astable", res_555["spice_netlist"])
        self.assertIn("<svg", res_555["schematic_svg"])
        self.assertIn("</svg>", res_555["schematic_svg"])

        # RC Lowpass
        res_rc = pcb.execute({"circuit_type": "rc_filter", "params": {"r": 1000, "c": 1e-7}})
        self.assertTrue(res_rc["success"])
        self.assertIn("Cutoff Freq", [m["label"] for m in res_rc["metrics"]])

    def test_silicon_eda_verilog_analysis(self):
        eda = SiliconEDATool()
        verilog_code = """
        module spi_slave(
            input wire sclk,
            input wire cs_n,
            input wire mosi,
            output reg miso
        );
            reg [7:0] shift_reg;
            always @(posedge sclk or posedge cs_n) begin
                if (cs_n) shift_reg <= 8'h00;
                else shift_reg <= {shift_reg[6:0], mosi};
            end
            always @(negedge sclk) begin
                miso <= shift_reg[7];
            end
        endmodule
        """
        res = eda.execute({"code": verilog_code, "target_clock_mhz": 50})
        self.assertTrue(res["success"])
        self.assertEqual(res["module_name"], "spi_slave")
        self.assertIn("sclk", res["clock_domains"])
        self.assertEqual(res["render_type"], "silicon_eda")
        metric_dict = {m["label"]: m["value"] for m in res["metrics"]}
        self.assertIn("Est. LUTs", metric_dict)
        self.assertIn("Est. FFs", metric_dict)

    def test_robotics_kinematics_dh_forward_chain(self):
        rob = RoboticsEngineTool()
        # Home position (all 0 degrees)
        res_home = rob.execute({"arm_type": "6dof_industrial", "joint_angles_deg": [0, 0, 0, 0, 0, 0]})
        self.assertTrue(res_home["success"])
        self.assertEqual(res_home["render_type"], "robotics")
        self.assertEqual(len(res_home["joint_chain"]), 7)  # Base + 6 joints
        self.assertGreater(res_home["reach_mm"], 500.0)

        # 90-degree waist rotation test: verifies exact SO(3) coordinate transformation
        res_rot = rob.execute({"arm_type": "6dof_industrial", "joint_angles_deg": [90, 0, 0, 0, 0, 0]})
        self.assertTrue(res_rot["success"])
        # Total reach from base must be invariant under waist rotation
        self.assertAlmostEqual(res_home["reach_mm"], res_rot["reach_mm"], delta=0.5)
        # Z-coordinate must be identical
        self.assertAlmostEqual(res_home["end_effector"]["z"], res_rot["end_effector"]["z"], delta=0.5)
        # Verify 90-deg rotation: x' == -y_home, y' == x_home
        self.assertAlmostEqual(res_rot["end_effector"]["x"], -res_home["end_effector"]["y"], delta=0.5)
        self.assertAlmostEqual(res_rot["end_effector"]["y"], res_home["end_effector"]["x"], delta=0.5)

    def test_cad_recompute_dispatch(self):
        # Test real-time slider recompute via tool dispatcher
        recompute_args = {
            "shape": "enclosure",
            "title": "Tactile Slider Test",
            "params": {"width": 140.0, "length": 90.0, "height": 40.0, "wall": 3.0}
        }
        res = tools.dispatch_tool("cad_model_generate", recompute_args)
        self.assertTrue(res["success"])
        self.assertEqual(res["parameters"]["width"], 140.0)
        self.assertEqual(res["parameters"]["length"], 90.0)
        self.assertEqual(res["parameters"]["height"], 40.0)
        self.assertEqual(res["parameters"]["wall"], 3.0)
        self.assertIn("stl_base64", res)
        self.assertGreater(len(res["mesh"]["positions"]), 0)

    def test_ingest_file_dimension_extraction(self):
        sample_doc = (
            "Sensor Module Spec Sheet\n"
            "Dimensions: 120mm x 80mm x 25mm\n"
            "Operating Voltage: 5V DC at 200mA\n"
            "Requires custom snap-fit enclosure and mounting holes."
        )
        lines = sample_doc.splitlines()
        dim_matches = re.findall(r"(\d+(?:\.\d+)?)\s*(?:mm|cm|m|in|\"|V|mA|A|Hz|kHz|MHz|Ω|kΩ)", sample_doc)
        self.assertIn("120", dim_matches)
        self.assertIn("80", dim_matches)
        self.assertIn("25", dim_matches)
        self.assertIn("5", dim_matches)
        self.assertIn("200", dim_matches)


    def test_kuzu_stem_graph_vendored_traversal(self):
        from knowledge_graph.kuzu_stem_graph import VigyanSTEMGraph
        kg = VigyanSTEMGraph()
        self.assertTrue(pathlib.Path(kg.db_path).exists())
        ctx = kg.query_multihop_context(["semiconductor", "mosfet"])
        self.assertGreater(len(ctx), 50)
        self.assertIn("Law", ctx)

    def test_robotics_and_wavedrom_recompute_dispatch(self):
        # 1. Robotics Recompute Dispatch
        rob_args = {
            "arm_type": "6dof_industrial",
            "joint_angles_deg": [0, 30, -45, 0, 15, 0]
        }
        res_rob = tools.dispatch_tool("robotics_kinematics", rob_args)
        self.assertTrue(res_rob["success"])
        self.assertIn("end_effector", res_rob)
        self.assertIn("reach_mm", res_rob)

        # 2. WaveDrom Recompute Dispatch
        wave_args = {
            "protocol": "axi4_stream",
            "title": "AXI4 Burst"
        }
        res_wave = tools.dispatch_tool("wavedrom_generate", wave_args)
        self.assertTrue(res_wave["success"])
        self.assertIn("wavedrom_spec", res_wave)


if __name__ == "__main__":
    unittest.main()

