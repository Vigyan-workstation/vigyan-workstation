"""
BaseTool contract for Vigyan Pro Desktop modular STEM plugins.
Strictly permissive open-source (Apache 2.0 / MIT).
100% offline, air-gapped, zero cloud telemetry.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseTool(ABC):
    """Abstract base class for all Vigyan Desktop STEM tools."""

    name: str = "base_tool"
    description: str = "Base STEM tool"
    render_type: str = "json"  # "threejs_cad", "wavedrom", "pcb_circuit", "silicon_eda", "robotics", "plotly"

    @abstractmethod
    def get_parameters_schema(self) -> Dict[str, Any]:
        """Return JSON Schema for the tool's expected arguments."""
        pass

    @abstractmethod
    def execute(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute tool and return structured payload for frontend card rendering."""
        pass

    def to_system_prompt_spec(self) -> str:
        """Format concise description and call pattern for model system prompt."""
        schema = self.get_parameters_schema()
        return f"- <tool_call>{{\"name\": \"{self.name}\", \"arguments\": {schema.get('example', {})}}}</tool_call> ({self.description})"
