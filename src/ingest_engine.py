"""
Sovereign Ingestion & CPU OCR Engine for Vigyan Pro Desktop.
Performs offline Tesseract OCR on images and Poppler pdftotext extraction on PDFs.
Permissive Open-Source (Apache 2.0 / MIT). 100% offline, air-gapped.
"""

import base64
import os
import pathlib
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional

TESSDATA_DIR = pathlib.Path.home() / ".vigyan" / "tessdata"


def get_tessdata_prefix() -> Optional[str]:
    """Return valid TESSDATA_PREFIX path if available."""
    if (TESSDATA_DIR / "eng.traineddata").exists():
        return str(TESSDATA_DIR)
    if pathlib.Path("/usr/share/tessdata/eng.traineddata").exists():
        return "/usr/share/tessdata"
    return None


def extract_text_from_image_bytes(img_bytes: bytes) -> str:
    """Run native CPU Tesseract OCR on image bytes without neural model overhead."""
    tess_bin = shutil.which("tesseract")
    if not tess_bin:
        return ""

    prefix = get_tessdata_prefix()
    env = os.environ.copy()
    if prefix:
        env["TESSDATA_PREFIX"] = prefix

    try:
        proc = subprocess.run(
            [tess_bin, "stdin", "stdout", "--psm", "6"],
            input=img_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
            timeout=5.0,
        )
        return proc.stdout.decode("utf-8", errors="replace").strip()
    except Exception:
        return ""


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract clean text and formulas from PDF bytes using pdftotext."""
    pdf_bin = shutil.which("pdftotext")
    if not pdf_bin:
        return ""

    try:
        proc = subprocess.run(
            [pdf_bin, "-", "-"],
            input=pdf_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=4.0,
        )
        return proc.stdout.decode("utf-8", errors="replace").strip()
    except Exception:
        return ""


def analyze_ingested_content(filename: str, raw_text: str) -> Dict[str, Any]:
    """Parse engineering metrics, dimensions, pinouts, and suggest 1-click actions."""
    clean_text = raw_text.strip()
    
    # 1. Search for 3D physical dimensions like 140x90x35mm or 140*90*35
    dim_3d = re.findall(r"(\d+(?:\.\d+)?)\s*(?:x|\*)\s*(\d+(?:\.\d+)?)\s*(?:x|\*)\s*(\d+(?:\.\d+)?)", clean_text, re.IGNORECASE)
    
    # 2. Search for physical and electrical metrics
    metrics_matches = re.findall(
        r"(\d+(?:\.\d+)?\s*(?:mm|cm|m|in|\"|V|mV|kV|mA|A|Hz|kHz|MHz|GHz|Ω|kΩ|MΩ|uF|nF|pF))",
        clean_text,
        re.IGNORECASE
    )

    detected_metrics: List[str] = []
    if dim_3d:
        w, l, h = dim_3d[0]
        detected_metrics.append(f"Dimensions: {w} × {l} × {h} mm")
    
    for m in metrics_matches[:6]:
        if m not in detected_metrics:
            detected_metrics.append(m.strip())

    # 3. Determine natural 1-click engineering actions
    clean_lower = clean_text.lower()
    suggested_actions: List[str] = []

    if dim_3d or any(w in clean_lower for w in ("dimension", "enclosure", "box", "mount", "wall", "thickness", "case", "housing")):
        if dim_3d:
            w, l, h = dim_3d[0]
            suggested_actions.append(f"Synthesize 3D CAD Enclosure ({w}x{l}x{h}mm)")
        else:
            suggested_actions.append("Synthesize 3D CAD Enclosure")

    if any(w in clean_lower for w in ("pin", "voltage", "circuit", "vcc", "gnd", "resistor", "capacitor", "555", "ic", "led")):
        suggested_actions.append("Generate KiCad PCB Netlist")

    if any(w in clean_lower for w in ("gear", "teeth", "module", "pitch", "spur")):
        suggested_actions.append("Synthesize 3D Parametric Gear")

    if not suggested_actions:
        suggested_actions = ["Synthesize 3D CAD Enclosure", "Evaluate Mathematical Proof"]

    # 4. Formulate executive human summary
    if clean_text:
        first_lines = [line.strip() for line in clean_text.splitlines() if line.strip()][:4]
        preview_sample = " · ".join(first_lines)
        if len(preview_sample) > 160:
            preview_sample = preview_sample[:157] + "…"
        summary = f"Detected in '{filename}': {preview_sample}"
    else:
        summary = f"Ingested '{filename}'. Ready for sovereign engineering synthesis."

    return {
        "success": True,
        "filename": filename,
        "text": clean_text[:2000] if clean_text else f"Imported {filename}",
        "summary": summary,
        "metrics": detected_metrics,
        "suggested_actions": suggested_actions,
    }
