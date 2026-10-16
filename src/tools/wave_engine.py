"""
WaveDrom Engine Plugin for Vigyan Pro Desktop.
Permissive Open-Source (Apache 2.0).
Digital bus timing diagram generator for hardware engineering.
100% offline, air-gapped, zero cloud telemetry.
"""

from typing import Any, Dict, List, Optional
from .base import BaseTool


STANDARD_BUS_PATTERNS = {
    "spi_master": {
        "title": "SPI Master Bus Transaction (Mode 0)",
        "signal": [
            {"name": "CS_n", "wave": "10.......1"},
            {"name": "SCLK", "wave": "0.p.......0"},
            {"name": "MOSI", "wave": "x2.3.4.5.x", "data": ["0x9F", "0x00", "0x00", "0xAA"]},
            {"name": "MISO", "wave": "x..2.3.4.x", "data": ["0xEF", "0x40", "0x18"]}
        ]
    },
    "i2c_bus": {
        "title": "I2C 7-Bit Address Read Cycle with ACK",
        "signal": [
            {"name": "SCL", "wave": "1.n.n.n.n.n.n.n.n.1"},
            {"name": "SDA", "wave": "102.3.4.5.6.7.8.0.1", "data": ["A6", "A5", "A4", "A3", "A2", "A1", "R/W", "ACK"]}
        ]
    },
    "uart_frame": {
        "title": "UART 8N1 Frame (115200 Baud)",
        "signal": [
            {"name": "BaudClk", "wave": "p................."},
            {"name": "TX/RX",   "wave": "102.3.4.5.6.7.8.9.1.", "data": ["START", "D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "STOP"]}
        ]
    },
    "axi4_stream": {
        "title": "AXI4-Stream Handshake & Packet Burst",
        "signal": [
            {"name": "ACLK",    "wave": "p........"},
            {"name": "ARESETn", "wave": "01......."},
            {"name": "TVALID",  "wave": "0.1...0.."},
            {"name": "TREADY",  "wave": "0...1...."},
            {"name": "TDATA",   "wave": "x.3.4.5.x", "data": ["Header", "Payload0", "Payload1"]},
            {"name": "TLAST",   "wave": "0.....10."}
        ]
    }
}


class WaveEngineTool(BaseTool):
    name = "wavedrom_generate"
    description = "Generate digital timing diagrams and bus waveforms (SPI, I2C, UART, AXI, custom digital logic) using WaveDrom."
    render_type = "wavedrom"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "protocol": {
                    "type": "string",
                    "enum": ["spi_master", "i2c_bus", "uart_frame", "axi4_stream", "custom"],
                    "description": "Standard digital bus protocol or 'custom'"
                },
                "title": {"type": "string", "description": "Title of the timing diagram"},
                "signal": {
                    "type": "array",
                    "description": "WaveDrom signal definitions array: [{'name': 'CLK', 'wave': 'p...'}, ...]"
                },
                "config": {"type": "object", "description": "WaveDrom config options (e.g. hscale)"}
            },
            "required": ["protocol"],
            "example": {
                "protocol": "spi_master",
                "title": "SPI Read Command & Payload Transfer"
            }
        }

    def execute(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        protocol = (arguments.get("protocol") or "spi_master").lower()
        title = arguments.get("title")
        custom_signals = arguments.get("signal")
        config = arguments.get("config") or {"hscale": 1}

        if protocol in STANDARD_BUS_PATTERNS and not custom_signals:
            pattern = STANDARD_BUS_PATTERNS[protocol]
            spec_title = title or pattern["title"]
            spec_signals = pattern["signal"]
        else:
            spec_title = title or "Digital Bus Timing Diagram"
            spec_signals = custom_signals or [
                {"name": "CLK", "wave": "p......"},
                {"name": "REQ", "wave": "0.1..0."},
                {"name": "ACK", "wave": "0..1..0"}
            ]

        wavedrom_spec = {
            "signal": spec_signals,
            "config": config,
            "head": {"text": spec_title, "tick": 0}
        }

        # Calculate metrics
        num_signals = len(spec_signals)
        max_wave_len = max((len(s.get("wave", "")) for s in spec_signals if isinstance(s, dict)), default=0)

        return {
            "success": True,
            "tool": self.name,
            "render_type": self.render_type,
            "title": spec_title,
            "protocol": protocol,
            "wavedrom_spec": wavedrom_spec,
            "metrics": [
                {"label": "Protocol", "value": protocol.upper()},
                {"label": "Signals", "value": str(num_signals)},
                {"label": "Clock Cycles", "value": str(max_wave_len)},
                {"label": "Engine", "value": "WaveDrom Native (Offline)"}
            ]
        }
