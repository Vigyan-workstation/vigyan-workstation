"""
Silicon EDA & Verilog Tool Plugin for Vigyan Pro Desktop.
Permissive Open-Source (ISC / MIT).
Verilog-2001 / SystemVerilog static analysis & RTL cell synthesis estimation.
100% offline, air-gapped, zero cloud telemetry.
"""

import re
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Optional
from .base import BaseTool


class SiliconEDATool(BaseTool):
    name = "verilog_analyze"
    description = "Analyze Verilog RTL modules, detect clock domains, inspect ports, and estimate FPGA/ASIC cell counts (LUTs, FFs, MUXes)."
    render_type = "silicon_eda"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Verilog module code"},
                "target_clock_mhz": {"type": "number", "description": "Target clock frequency in MHz (default 50)"}
            },
            "required": ["code"],
            "example": {
                "code": "module counter_4bit(input clk, input rst_n, output reg [3:0] q);\nalways @(posedge clk or negedge rst_n) begin\n  if (!rst_n) q <= 4'b0;\n  else q <= q + 1;\nend\nendmodule",
                "target_clock_mhz": 100
            }
        }

    def execute(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        code = arguments.get("code") or ""
        clk_mhz = float(arguments.get("target_clock_mhz") or 50.0)

        # 1. Parse module name
        mod_match = re.search(r"\bmodule\s+([a-zA-Z0-9_]+)", code)
        mod_name = mod_match.group(1) if mod_match else "rtl_module"

        # 2. Extract ports
        inputs = re.findall(r"\binput\s+(?:wire\s+)?(?:\[[^\]]+\]\s+)?([a-zA-Z0-9_,\s]+);", code)
        outputs = re.findall(r"\boutput\s+(?:reg\s+|wire\s+)?(?:\[[^\]]+\]\s+)?([a-zA-Z0-9_,\s]+);", code)

        # Count total IO bits
        input_names = [p.strip() for line in inputs for p in line.split(",") if p.strip()]
        output_names = [p.strip() for line in outputs for p in line.split(",") if p.strip()]

        # 3. Detect clock domains
        clk_matches = re.findall(r"@\s*\(\s*posedge\s+([a-zA-Z0-9_]+)", code)
        clk_domains = list(set(clk_matches)) or ["clk"]

        # 4. Sequential state bits / Flip-flops estimation
        reg_defs = re.findall(r"\breg\s+(?:\[(\d+):(\d+)\])?\s*([a-zA-Z0-9_,\s]+);", code)
        est_ffs = 0
        for msb, lsb, names in reg_defs:
            width = abs(int(msb) - int(lsb)) + 1 if msb and lsb else 1
            num_names = len([n for n in names.split(",") if n.strip()])
            est_ffs += width * num_names
        est_ffs = max(len(clk_matches) * 2, est_ffs)

        # 5. Combinational complexity / LUTs estimation
        assigns = len(re.findall(r"\bassign\s+", code))
        always_blocks = len(re.findall(r"\balways\s*@", code))
        operators = len(re.findall(r"[\+\-\*\&\|\^\~]", code))
        est_luts = max(4, assigns * 2 + always_blocks * 6 + operators * 3)

        engine_used = "Vigyan Sovereign RTL Static Estimator"

        # 6. Optional Yosys binary invocation if available
        yosys_bin = shutil.which("yosys")
        if yosys_bin:
            try:
                with tempfile.NamedTemporaryFile("w", suffix=".v", delete=True) as tmp_v:
                    tmp_v.write(code)
                    tmp_v.flush()
                    script = f"read_verilog {tmp_v.name}; synth -top {mod_name}; stat;"
                    proc = subprocess.run([yosys_bin, "-p", script], capture_output=True, text=True, timeout=4.0)
                    if proc.returncode == 0:
                        engine_used = "Yosys Open Synthesis Suite"
                        # Parse yosys stat output
                        stat_match = re.search(r"Number of cells:\s+(\d+)", proc.stdout)
                        if stat_match:
                            est_luts = int(stat_match.group(1))
            except Exception:
                pass

        period_ns = round(1000.0 / clk_mhz, 2)

        return {
            "success": True,
            "tool": self.name,
            "render_type": self.render_type,
            "module_name": mod_name,
            "engine": engine_used,
            "metrics": [
                {"label": "Module", "value": mod_name},
                {"label": "Est. LUTs", "value": str(est_luts)},
                {"label": "Est. FFs", "value": str(est_ffs)},
                {"label": "Clock Target", "value": f"{clk_mhz} MHz ({period_ns} ns)"},
                {"label": "Domains", "value": ", ".join(clk_domains)},
                {"label": "IO Pins", "value": f"{len(input_names)} in / {len(output_names)} out"}
            ],
            "ports": {
                "inputs": input_names,
                "outputs": output_names
            },
            "clock_domains": clk_domains
        }
