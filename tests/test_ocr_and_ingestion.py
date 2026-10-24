"""
Unit Tests for Sovereign Ingestion & CPU OCR Engine in Vigyan Pro Desktop.
Verifies offline Tesseract OCR, dimension parsing, and action chip generation.
"""

import base64
import io
import json
import pathlib
import sys
import unittest
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import ingest_engine
import launch_desktop


class TestOCRandIngestion(unittest.TestCase):
    def test_image_ocr_dimension_extraction(self):
        # Create synthetic test image with clean text
        img = Image.new("RGB", (600, 120), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((30, 40), "Dimensions: 140x90x35mm  Voltage: 5V DC", fill=(0, 0, 0))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        # Run sovereign CPU OCR
        text = ingest_engine.extract_text_from_image_bytes(img_bytes)
        self.assertTrue(len(text) > 0, "OCR should extract text from synthetic image")

        # Analyze extracted metrics
        res = ingest_engine.analyze_ingested_content("test_schematic.png", text)
        self.assertTrue(res["success"])
        self.assertEqual(res["filename"], "test_schematic.png")
        
        # Check that 1-click action buttons were generated
        actions = res["suggested_actions"]
        self.assertTrue(any("3D" in a or "CAD" in a or "Enclosure" in a for a in actions))

    def test_plain_text_and_metrics_analysis(self):
        doc = (
            "Raspberry Pi Zero W Enclosure Specifications\n"
            "Outer Dimensions: 65x30x12mm with 2mm wall thickness\n"
            "Input Power: 5V DC at 1.2A via Micro-USB\n"
            "Mounting: 4 corner holes for M2.5 screws"
        )
        res = ingest_engine.analyze_ingested_content("pi_zero_specs.txt", doc)
        self.assertTrue(res["success"])
        
        metrics = res["metrics"]
        self.assertTrue(any("65" in m and "30" in m and "12" in m for m in metrics))
        
        actions = res["suggested_actions"]
        self.assertIn("Synthesize 3D CAD Enclosure (65x30x12mm)", actions)

    def test_pcb_electronics_detection(self):
        doc = (
            "Astable 555 Timer Circuit\n"
            "Components: NE555, R1=10kΩ, R2=47kΩ, C1=1uF\n"
            "Pin 4 (Reset) tied to VCC, Pin 8 to 5V"
        )
        res = ingest_engine.analyze_ingested_content("555_timer.txt", doc)
        self.assertTrue(res["success"])
        actions = res["suggested_actions"]
        self.assertIn("Generate KiCad PCB Netlist", actions)


if __name__ == "__main__":
    unittest.main()
