"""
Modular STEM Tool Registry for Vigyan Pro Desktop.
Permissive Open-Source (Apache 2.0 / MIT / BSD-2 / ISC).
100% offline, air-gapped, zero cloud telemetry.
"""

from typing import Any, Dict, Optional
from .base import BaseTool
from .cad_engine import CADEngineTool
from .wave_engine import WaveEngineTool
from .pcb_engine import PCBEngineTool
from .silicon_eda import SiliconEDATool
from .robotics_engine import RoboticsEngineTool

_INSTANCES = [
    CADEngineTool(),
    WaveEngineTool(),
    PCBEngineTool(),
    SiliconEDATool(),
    RoboticsEngineTool()
]

TOOL_REGISTRY: Dict[str, BaseTool] = {tool.name: tool for tool in _INSTANCES}


def get_all_tools() -> Dict[str, BaseTool]:
    """Return all registered STEM tools."""
    return TOOL_REGISTRY


def get_tool_schemas_prompt() -> str:
    """Generate dynamic system prompt instructions for all registered STEM tools."""
    lines = [
        "- <tool_call>{\"name\": \"cad_model_generate\", \"arguments\": {\"shape\": \"enclosure\", \"title\": \"Project Box (120x80x35mm)\", \"params\": {\"width\": 120, \"length\": 80, \"height\": 35, \"wall\": 2.5}}}</tool_call>",
        "- <tool_call>{\"name\": \"wavedrom_generate\", \"arguments\": {\"protocol\": \"spi_master\", \"title\": \"SPI Read Cycle\"}}</tool_call>",
        "- <tool_call>{\"name\": \"pcb_netlist_generate\", \"arguments\": {\"circuit_type\": \"555_timer\", \"title\": \"555 Astable Pulse Generator\", \"params\": {\"r1\": 10000, \"r2\": 47000, \"c1\": 1e-6}}}</tool_call>",
        "- <tool_call>{\"name\": \"verilog_analyze\", \"arguments\": {\"code\": \"module counter(input clk, output reg [3:0] q); always @(posedge clk) q <= q + 1; endmodule\", \"target_clock_mhz\": 100}}</tool_call>",
        "- <tool_call>{\"name\": \"robotics_kinematics\", \"arguments\": {\"arm_type\": \"6dof_industrial\", \"joint_angles_deg\": [0, 45, -30, 0, 15, 0]}}</tool_call>"
    ]
    return "\n".join(lines)


def dispatch_tool(name: str, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Safely dispatch tool call to registered handler with error trapping."""
    tool = TOOL_REGISTRY.get(name)
    if not tool:
        return {"success": False, "error": f"Tool '{name}' is not registered in Vigyan STEM tools"}
    try:
        res = tool.execute(arguments, context=context)
        return res
    except Exception as exc:
        return {"success": False, "tool": name, "error": str(exc)}
