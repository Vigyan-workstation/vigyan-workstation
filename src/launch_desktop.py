#!/usr/bin/env python3
"""
Vigyan Pro Sovereign Studio - Native Desktop WebKitGTK Application
Pitch-Black Obsidian STEM Studio with Smart Hybrid GPU+CPU Compute Engine,
Embedded Neuro-Symbolic Bridge (SymPy AST + KùzuDB GraphRAG), LaTeX, and WebGL.
Zero Browser Chrome. 100% Native Desktop Window.
"""

import sys
import os
import re
import glob
import math
import ast
import json
import time
import shutil
import signal
import threading
import subprocess
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Any, List, Optional

# Auto-inject virtualenv site-packages so SymPy, KùzuDB, LanceDB are always available
for _p in glob.glob(os.path.expanduser("~/.venv-rag/lib/python*/site-packages")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Set Ollama hybrid compute acceleration flags before spawning daemon
os.environ.setdefault("OLLAMA_FLASH_ATTENTION", "1")
os.environ.setdefault("OLLAMA_KV_CACHE_TYPE", "q8_0")
os.environ.setdefault("OLLAMA_NUM_PARALLEL", "1")
os.environ.setdefault("OLLAMA_IGPU_ENABLE", "1")
os.environ.setdefault("OLLAMA_ORIGINS", "*")

from ollama_supervisor import OllamaSupervisor

try:
    import tools
except Exception:
    tools = None

try:
    from version import __version__
except Exception:
    __version__ = "2.7.0-beta.1"

try:
    import psutil
except ImportError:
    psutil = None

# ==============================================================================
# 1. SMART HYBRID GPU + CPU HARDWARE PROFILER & ALLOCATOR
# ==============================================================================
_ACTIVE_COMPUTE_MODE = "auto"  # "auto" | "max_gpu" | "balanced" | "cpu_eco"
_STATIC_HW_CACHE: Optional[ Dict[str, Any] ] = None


def _read_sysfs_int(path: str) -> Optional[int]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except Exception:
        return None


def _read_sysfs_str(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return None


def _discover_static_hardware() -> Dict[str, Any]:
    """One-time hardware topology discovery (<50ms at startup, cached forever)."""
    global _STATIC_HW_CACHE
    if _STATIC_HW_CACHE is not None:
        return _STATIC_HW_CACHE

    # 1. CPU Physical vs Logical Cores
    logical_cores = os.cpu_count() or 4
    physical_cores = max(1, logical_cores // 2)
    if psutil:
        try:
            lc = psutil.cpu_count(logical=True)
            pc = psutil.cpu_count(logical=False)
            if lc:
                logical_cores = lc
            if pc:
                physical_cores = pc
        except Exception:
            pass

    cpu_model = "Generic x86_64/ARM64 Processor"
    if sys.platform.startswith("linux") and os.path.exists("/proc/cpuinfo"):
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if "model name" in line or "Hardware" in line:
                        cpu_model = line.split(":", 1)[1].strip()
                        break
        except Exception:
            pass
    elif sys.platform == "darwin":
        try:
            res = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=0.4
            )
            if res.returncode == 0 and res.stdout.strip():
                cpu_model = res.stdout.strip()
        except Exception:
            pass

    # 2. Total System RAM
    ram_total_gb = 8.0
    if psutil:
        try:
            ram_total_gb = round(psutil.virtual_memory().total / (1024 ** 3), 2)
        except Exception:
            pass

    # 3. GPU Topology Discovery (NVIDIA, Linux DRM sysfs AMD/Intel, Apple Metal, Windows WMI)
    has_nvidia = shutil.which("nvidia-smi") is not None
    nvidia_name = None
    if has_nvidia:
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=0.4
            )
            if res.returncode == 0 and res.stdout.strip():
                nvidia_name = res.stdout.strip().splitlines()[0].strip()
            else:
                has_nvidia = False
        except Exception:
            has_nvidia = False

    drm_card_dir = None
    gpu_vendor = "none"
    gpu_name = nvidia_name or "CPU Vector Engine"

    if sys.platform.startswith("linux"):
        for card_path in sorted(glob.glob("/sys/class/drm/card[0-9]/device")):
            vendor_hex = (_read_sysfs_str(os.path.join(card_path, "vendor")) or "").lower()
            vram_tot = _read_sysfs_int(os.path.join(card_path, "mem_info_vram_total"))
            busy_path = os.path.join(card_path, "gpu_busy_percent")
            if vram_tot is not None or os.path.exists(busy_path) or vendor_hex in ("0x1002", "0x8086", "0x10de"):
                drm_card_dir = card_path
                if vendor_hex == "0x1002":
                    gpu_vendor = "amd"
                    gpu_name = "AMD Radeon Graphics"
                elif vendor_hex == "0x8086":
                    gpu_vendor = "intel"
                    gpu_name = "Intel Integrated/Arc GPU"
                elif vendor_hex == "0x10de":
                    gpu_vendor = "nvidia"
                    gpu_name = nvidia_name or "NVIDIA GPU"
                break

        # Enrich marketing name from lspci once at startup
        if shutil.which("lspci"):
            try:
                res = subprocess.run(
                    ["lspci"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=0.4
                )
                if res.returncode == 0:
                    for line in res.stdout.splitlines():
                        if any(k in line for k in ("VGA compatible controller", "3D controller", "Display controller")):
                            parts = line.split(":", 2)
                            if len(parts) >= 3:
                                desc = parts[2].strip()
                                bracket = re.findall(r"\[([^\]]+)\]", desc)
                                if bracket:
                                    # Pick the most descriptive bracketed model name
                                    best = [b for b in bracket if not b.startswith("1002:") and not b.startswith("8086:") and not b.startswith("10de:")]
                                    if best:
                                        gpu_name = best[-1]
                                    else:
                                        gpu_name = desc[:42]
                                else:
                                    gpu_name = desc[:42]
                                break
            except Exception:
                pass
    elif sys.platform == "darwin":
        if "Apple" in cpu_model:
            gpu_vendor = "apple_metal"
            gpu_name = f"{cpu_model} Metal GPU"

    _STATIC_HW_CACHE = {
        "cpu_model": cpu_model,
        "physical_cores": physical_cores,
        "logical_cores": logical_cores,
        "ram_total_gb": ram_total_gb,
        "has_nvidia": has_nvidia,
        "drm_card_dir": drm_card_dir,
        "gpu_vendor": gpu_vendor if not has_nvidia else "nvidia",
        "gpu_name": nvidia_name or gpu_name,
    }
    return _STATIC_HW_CACHE


def _read_power_state() -> Dict[str, Any]:
    """Fast zero-subprocess battery and AC power profile detection."""
    is_laptop = False
    on_battery = False
    battery_pct = 100

    if sys.platform.startswith("linux"):
        bat_dirs = glob.glob("/sys/class/power_supply/BAT*")
        if bat_dirs:
            is_laptop = True
            status = (_read_sysfs_str(os.path.join(bat_dirs[0], "status")) or "").lower()
            cap = _read_sysfs_int(os.path.join(bat_dirs[0], "capacity"))
            if cap is not None:
                battery_pct = cap
            if status == "discharging":
                on_battery = True
    elif psutil and hasattr(psutil, "sensors_battery"):
        try:
            bat = psutil.sensors_battery()
            if bat is not None:
                is_laptop = True
                battery_pct = int(round(bat.percent))
                on_battery = not bool(bat.power_plugged)
        except Exception:
            pass

    if not is_laptop:
        power_profile = "Desktop AC"
    elif on_battery:
        power_profile = f"Laptop Battery ({battery_pct}%)"
    else:
        power_profile = f"Laptop AC ({battery_pct}%)"

    return {
        "is_laptop": is_laptop,
        "on_battery": on_battery,
        "battery_pct": battery_pct,
        "power_profile": power_profile,
    }


def compute_hybrid_allocation(
    mode: str,
    hw: Dict[str, Any],
    gpu_metrics: Dict[str, Any],
    power: Dict[str, Any],
    ram_avail_gb: float,
) -> Dict[str, Any]:
    """
    Smart Hybrid GPU + CPU Compute Allocator.
    Computes optimal Ollama runtime options (num_gpu, num_thread, num_ctx, num_batch)
    based on hardware topology, VRAM + GTT headroom, physical CPU cores, and power state.
    """
    mode = (mode or "auto").lower()
    if mode not in ("auto", "max_gpu", "balanced", "cpu_eco"):
        mode = "auto"

    phys_cores = int(hw.get("physical_cores", 4))
    ram_total_gb = float(hw.get("ram_total_gb", 8.0))
    has_gpu = bool(gpu_metrics.get("has_gpu", False))
    is_apu = bool(gpu_metrics.get("is_apu", False))
    vram_total_mb = float(gpu_metrics.get("vram_total_mb", 0.0))
    gtt_total_mb = float(gpu_metrics.get("gtt_total_mb", 0.0))
    effective_gpu_mem_mb = vram_total_mb + (gtt_total_mb * 0.65 if is_apu else 0.0)
    on_battery = bool(power.get("on_battery", False))
    battery_pct = int(power.get("battery_pct", 100))

    # 1. Thread allocation: bind to physical cores; throttle on battery to prevent heat & drain
    if mode == "cpu_eco" or (mode == "auto" and on_battery and battery_pct < 40):
        num_thread = max(2, phys_cores - 2)
    elif on_battery:
        num_thread = max(2, phys_cores - 1)
    else:
        num_thread = phys_cores

    # 2. Context window & batch scaling to prevent RAM/swap thrashing & OOM killer
    if ram_total_gb < 6.0 or ram_avail_gb < 2.5:
        num_ctx = 1024
        num_batch = 64
    elif ram_total_gb < 10.0:
        # 7-8 GB laptops (e.g., Ryzen 5 7520U with 6.95 GB usable RAM)
        # Lock to 1024-1536 context to keep KV cache minimal (~200MB instead of 1.2GB)
        num_ctx = 1024 if ram_avail_gb < 3.5 else 1536
        num_batch = 64
    elif ram_total_gb < 18.0:
        num_ctx = 4096
        num_batch = 256
    else:
        num_ctx = 16384 if mode == "max_gpu" and ram_total_gb >= 24.0 else 8192
        num_batch = 512

    # 3. Hybrid GPU + CPU Layer Split (num_gpu)
    if mode == "cpu_eco" or not has_gpu:
        num_gpu = 0
        strategy_label = "CPU Eco (AVX2 Physical Cores)" if mode == "cpu_eco" else "CPU Vector Engine"
    elif mode == "max_gpu":
        num_gpu = 99
        strategy_label = "Max GPU Offload (All Layers)"
    elif mode == "balanced":
        num_gpu = 16 if is_apu or vram_total_mb < 6000 else 28
        strategy_label = f"Balanced Split ({num_gpu} GPU L + {num_thread}C CPU)"
    else:
        # Smart Auto-Hybrid Policy ("auto")
        if on_battery and battery_pct < 20:
            num_gpu = 0
            strategy_label = "Battery Saver CPU Mode"
        elif not is_apu and vram_total_mb >= 6000:
            num_gpu = 99
            strategy_label = f"Full dGPU Offload ({num_thread}C Assist)"
        elif is_apu or effective_gpu_mem_mb >= 1500:
            # Integrated APU (like Radeon 610M with VRAM + GTT shared pool) or mid-VRAM GPU:
            # Split attention/FFN layers across GPU & physical CPU cores for best throughput without OOM
            if ram_avail_gb >= 3.2:
                num_gpu = 20 if not on_battery else 12
            elif ram_avail_gb >= 2.0:
                num_gpu = 12 if not on_battery else 8
            else:
                num_gpu = 0
            strategy_label = (
                f"Smart APU+CPU Hybrid ({num_gpu}L GPU / {num_thread}C CPU)"
                if num_gpu > 0
                else f"Smart Low-RAM CPU Guard ({num_thread}C CPU)"
            )
        elif vram_total_mb >= 2000:
            num_gpu = 18
            strategy_label = f"Smart Hybrid Split ({num_gpu}L GPU / {num_thread}C CPU)"
        else:
            num_gpu = 0
            strategy_label = f"Physical Core AVX ({num_thread}C CPU)"

    mode_titles = {
        "auto": "Auto Hybrid",
        "max_gpu": "Max GPU",
        "balanced": "Balanced Hybrid",
        "cpu_eco": "CPU Eco",
    }

    return {
        "mode": mode,
        "mode_label": mode_titles.get(mode, "Auto Hybrid"),
        "strategy_label": strategy_label,
        "num_gpu": num_gpu,
        "num_thread": num_thread,
        "num_ctx": num_ctx,
        "num_batch": num_batch,
        "flash_attention": True,
        "kv_cache_type": "q8_0",
    }


def get_system_telemetry(override_mode: Optional[str] = None) -> Dict[str, Any]:
    """
    Return comprehensive, zero-lag hardware & hybrid compute telemetry:
    CPU %, RAM %, GPU % & VRAM/GTT usage, Power Profile, and active Hybrid Compute options.
    """
    global _ACTIVE_COMPUTE_MODE
    if override_mode in ("auto", "max_gpu", "balanced", "cpu_eco"):
        _ACTIVE_COMPUTE_MODE = override_mode

    hw = _discover_static_hardware()
    power = _read_power_state()

    ram_pct = 0.0
    cpu_pct = 0.0
    ram_used_gb = 0.0
    ram_avail_gb = max(2.0, hw["ram_total_gb"] * 0.5)

    if psutil:
        try:
            vm = psutil.virtual_memory()
            ram_pct = float(vm.percent)
            ram_used_gb = round((vm.total - vm.available) / (1024 ** 3), 2)
            ram_avail_gb = round(vm.available / (1024 ** 3), 2)
            cpu_pct = float(psutil.cpu_percent(interval=None))
        except Exception:
            pass

    gpu_util = 0
    vram_used_mb = 0.0
    vram_total_mb = 0.0
    gtt_used_mb = 0.0
    gtt_total_mb = 0.0
    has_gpu = False
    is_apu = False
    gpu_info = "CPU Only"

    # Fast Path 1: Linux DRM sysfs (0.05ms, zero subprocesses)
    card_dir = hw.get("drm_card_dir")
    if card_dir and os.path.exists(card_dir) and not hw.get("has_nvidia"):
        has_gpu = True
        busy = _read_sysfs_int(os.path.join(card_dir, "gpu_busy_percent"))
        if busy is not None:
            gpu_util = busy
        vu = _read_sysfs_int(os.path.join(card_dir, "mem_info_vram_used"))
        vt = _read_sysfs_int(os.path.join(card_dir, "mem_info_vram_total"))
        gu = _read_sysfs_int(os.path.join(card_dir, "mem_info_gtt_used"))
        gt = _read_sysfs_int(os.path.join(card_dir, "mem_info_gtt_total"))

        if vt is not None:
            vram_used_mb = round((vu or 0) / (1024 ** 2), 1)
            vram_total_mb = round(vt / (1024 ** 2), 1)
        if gt is not None:
            gtt_used_mb = round((gu or 0) / (1024 ** 2), 1)
            gtt_total_mb = round(gt / (1024 ** 2), 1)

        if vram_total_mb < 2048 and gtt_total_mb > 0:
            is_apu = True
            combined_used_gb = (vram_used_mb + gtt_used_mb) / 1024.0
            combined_tot_gb = (vram_total_mb + gtt_total_mb) / 1024.0
            gpu_info = f"GPU {gpu_util}% | {combined_used_gb:.1f}/{combined_tot_gb:.1f} GB Unified"
        elif vram_total_mb > 0:
            gpu_info = f"GPU {gpu_util}% | {vram_used_mb/1024:.1f}/{vram_total_mb/1024:.1f} GB VRAM"
        else:
            gpu_info = f"GPU {gpu_util}% ({hw['gpu_name']})"

    # Path 2: NVIDIA SMI (if present)
    elif hw.get("has_nvidia"):
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=0.25
            )
            if res.returncode == 0 and res.stdout.strip():
                parts = [p.strip() for p in res.stdout.strip().split(",")]
                if len(parts) >= 3:
                    has_gpu = True
                    gpu_util = int(float(parts[0]))
                    vram_used_mb = float(parts[1])
                    vram_total_mb = float(parts[2])
                    gpu_info = f"GPU {gpu_util}% | {vram_used_mb/1024:.1f}/{vram_total_mb/1024:.1f} GB"
        except Exception:
            pass
    elif hw.get("gpu_vendor") == "apple_metal":
        has_gpu = True
        is_apu = True
        vram_total_mb = hw["ram_total_gb"] * 1024 * 0.75
        gpu_info = f"Metal Unified ({hw['ram_total_gb']:.0f} GB)"

    gpu_metrics = {
        "has_gpu": has_gpu,
        "is_apu": is_apu,
        "gpu_name": hw.get("gpu_name", "CPU Only"),
        "gpu_vendor": hw.get("gpu_vendor", "none"),
        "gpu_util": gpu_util,
        "vram_used_mb": vram_used_mb,
        "vram_total_mb": vram_total_mb,
        "gtt_used_mb": gtt_used_mb,
        "gtt_total_mb": gtt_total_mb,
    }

    hybrid = compute_hybrid_allocation(_ACTIVE_COMPUTE_MODE, hw, gpu_metrics, power, ram_avail_gb)
    ollama_options = {
        "num_gpu": hybrid["num_gpu"],
        "num_thread": hybrid["num_thread"],
        "num_ctx": hybrid["num_ctx"],
        "num_batch": hybrid["num_batch"],
    }

    return {
        "cpu_pct": cpu_pct,
        "cpu_percent": cpu_pct,
        "cpu_model": hw["cpu_model"],
        "physical_cores": hw["physical_cores"],
        "cpu_cores_physical": hw["physical_cores"],
        "logical_cores": hw["logical_cores"],
        "cpu_cores_logical": hw["logical_cores"],
        "ram_pct": ram_pct,
        "ram_percent": ram_pct,
        "ram_used_gb": ram_used_gb,
        "ram_total_gb": hw["ram_total_gb"],
        "ram_avail_gb": ram_avail_gb,
        "gpu_info": gpu_info,
        "gpu_available": has_gpu,
        "gpu_name": hw.get("gpu_name", "CPU Only"),
        "gpu_vendor": hw.get("gpu_vendor", "none"),
        "gpu_percent": gpu_util,
        "vram_used_mb": vram_used_mb,
        "vram_total_mb": vram_total_mb,
        "gtt_used_mb": gtt_used_mb,
        "gtt_total_mb": gtt_total_mb,
        "effective_vram_mb": round(vram_total_mb + gtt_total_mb, 1),
        "on_battery": power["on_battery"],
        "battery_percent": power["battery_pct"],
        "compute_mode": hybrid["mode"],
        "strategy_label": hybrid["strategy_label"],
        "ollama_options": ollama_options,
        "gpu": gpu_metrics,
        "power": power,
        "hybrid": hybrid,
    }


# ==============================================================================
# 2. EMBEDDED NEURO-SYMBOLIC ENGINE (SYMPY AST + KÙZUDB GRAPHRAG BRIDGE)
# ==============================================================================
MASTERPIECE_DIR = "/home/hello/vigyan_masterpiece"
if os.path.exists(MASTERPIECE_DIR) and MASTERPIECE_DIR not in sys.path:
    sys.path.append(MASTERPIECE_DIR)

_SYMPY_ENGINE = None
_STEM_GRAPH = None

try:
    from tools.sympy_math_engine import SymPyMathEngine as _ExtSymPyEngine
    _SYMPY_ENGINE = _ExtSymPyEngine()
except Exception:
    try:
        import sympy as sp

        class _FallbackSymPyEngine:
            def __init__(self):
                self.safe_dict = {
                    "x": sp.Symbol("x"), "y": sp.Symbol("y"), "z": sp.Symbol("z"),
                    "t": sp.Symbol("t"), "s": sp.Symbol("s"), "n": sp.Symbol("n", integer=True),
                    "k": sp.Symbol("k"), "R": sp.Symbol("R", positive=True),
                    "C": sp.Symbol("C", positive=True), "L": sp.Symbol("L", positive=True),
                    "pi": sp.pi, "e": sp.E, "E": sp.E, "oo": sp.oo, "inf": sp.oo,
                    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "exp": sp.exp,
                    "log": sp.log, "ln": sp.log, "sqrt": sp.sqrt, "diff": sp.diff,
                    "integrate": sp.integrate, "solve": sp.solve, "simplify": sp.simplify,
                    "expand": sp.expand, "factor": sp.factor, "limit": sp.limit,
                    "series": sp.series, "dsolve": sp.dsolve, "Matrix": sp.Matrix,
                    "Eq": sp.Eq, "symbols": sp.symbols, "Symbol": sp.Symbol, "sp": sp,
                }
                try:
                    from sympy.parsing.sympy_parser import (
                        parse_expr,
                        standard_transformations,
                        implicit_multiplication_application,
                        convert_xor
                    )
                    self._parse_expr = parse_expr
                    self._transformations = standard_transformations + (implicit_multiplication_application, convert_xor)
                except Exception:
                    self._parse_expr = None
                    self._transformations = None

            def _is_safe_ast(self, expr_str: str) -> bool:
                try:
                    tree = ast.parse(expr_str, mode="eval")
                    allowed_nodes = (
                        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
                        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow,
                        ast.FloorDiv, ast.Mod, ast.UAdd, ast.USub, ast.Name,
                        ast.Call, ast.Load, ast.Tuple, ast.List
                    )
                    for node in ast.walk(tree):
                        if not isinstance(node, allowed_nodes):
                            return False
                        if isinstance(node, ast.Name) and node.id not in self.safe_dict:
                            return False
                    return True
                except Exception:
                    return False

            def evaluate_expression(self, expr_str: str) -> Dict[str, Any]:
                s = expr_str.strip()
                try:
                    if self._parse_expr:
                        res = self._parse_expr(s, local_dict=self.safe_dict, transformations=self._transformations)
                    elif self._is_safe_ast(s):
                        res = eval(s, {"__builtins__": {}}, dict(self.safe_dict))
                    else:
                        return {"success": False, "error": "Mathematical expression contains disallowed syntax"}
                    latex_res = sp.latex(res) if isinstance(res, (sp.Basic, sp.Matrix)) else str(res)
                    num = None
                    if hasattr(res, "evalf") and not getattr(res, "free_symbols", None):
                        try:
                            num = float(res.evalf(6))
                        except Exception:
                            num = None
                    elif isinstance(res, (int, float)):
                        num = float(res)
                    return {"success": True, "result": str(res), "latex": latex_res, "numeric_approx": num}
                except Exception as exc:
                    try:
                        if self._is_safe_ast(s):
                            res = eval(s, {"__builtins__": {}}, dict(self.safe_dict))
                            latex_res = sp.latex(res) if isinstance(res, (sp.Basic, sp.Matrix)) else str(res)
                            num = float(res.evalf(6)) if hasattr(res, "evalf") and not getattr(res, "free_symbols", None) else None
                            return {"success": True, "result": str(res), "latex": latex_res, "numeric_approx": num}
                        return {"success": False, "error": str(exc)}
                    except Exception:
                        return {"success": False, "error": str(exc)}

        _SYMPY_ENGINE = _FallbackSymPyEngine()
    except Exception:
        _SYMPY_ENGINE = None

# Curated deterministic GraphRAG knowledge base (always available even if KùzuDB is locked)
CURATED_GRAPH_AXIOMS = [
    {
        "keywords": ["ohm", "resistor", "voltage", "current", "resistance"],
        "law": "Ohm's Law & Joule Heating",
        "domain": "Circuits",
        "equation": "V = I \\cdot R, \\quad P = I^2 R = \\frac{V^2}{R}",
        "axiom": "Potential difference across an ideal conductor is proportional to current; microscopic form J = sigma E.",
    },
    {
        "keywords": ["rc", "cutoff", "filter", "sallen", "capacitor", "time constant"],
        "law": "RC Filter & Cutoff Frequency",
        "domain": "Signal Processing",
        "equation": "\\tau = R C, \\quad f_c = \\frac{1}{2\\pi R C}, \\quad H(s) = \\frac{1}{1 + s R C}",
        "axiom": "3dB corner frequency where output power drops by 50% (-3 dB) with -45 deg phase shift.",
    },
    {
        "keywords": ["rlc", "resonance", "resonant", "tank", "inductor", "q factor"],
        "law": "RLC Resonance & Quality Factor",
        "domain": "RF & Circuits",
        "equation": "f_0 = \\frac{1}{2\\pi\\sqrt{LC}}, \\quad Q = \\frac{1}{R}\\sqrt{\\frac{L}{C}}",
        "axiom": "At resonance X_L = X_C, reactive impedance cancels and energy oscillates between magnetic (L) and electric (C) fields.",
    },
    {
        "keywords": ["555", "astable", "timer", "oscillator", "pwm", "duty"],
        "law": "NE555 Astable Multivibrator Timing",
        "domain": "Analog ICs",
        "equation": "f = \\frac{1.44}{(R_A + 2 R_B) C}, \\quad D = \\frac{R_A + R_B}{R_A + 2 R_B}",
        "axiom": "Capacitor charges between 1/3 Vcc and 2/3 Vcc comparator thresholds via RA+RB and discharges through RB.",
    },
    {
        "keywords": ["mosfet", "saturation", "finfet", "gaa", "transistor", "vgs", "vds", "dibl", "subthreshold"],
        "law": "MOSFET Saturation & Subthreshold Conduction",
        "domain": "Semiconductor VLSI",
        "equation": "I_D = \\frac{1}{2}\\mu_n C_{ox}\\frac{W}{L}(V_{GS}-V_{th})^2(1+\\lambda V_{DS}), \\quad SS = \\ln(10)\\frac{k_B T}{q}\\left(1+\\frac{C_d}{C_{ox}}\\right)",
        "axiom": "Pinch-off saturation occurs for Vds >= Vgs - Vth; room-temperature thermionic subthreshold limit is 60 mV/decade.",
    },
    {
        "keywords": ["bandgap", "silicon", "gaas", "gan", "pn", "junction", "depletion", "diode", "shockley"],
        "law": "PN Junction Depletion & Shockley Diode Law",
        "domain": "Solid-State Physics",
        "equation": "I = I_s\\left(e^{\\frac{qV}{n k_B T}} - 1\\right), \\quad V_{bi} = \\frac{k_B T}{q}\\ln\\left(\\frac{N_A N_D}{n_i^2}\\right)",
        "axiom": "Si Eg = 1.12 eV (indirect), GaAs Eg = 1.42 eV (direct), GaN Eg = 3.40 eV (wide bandgap).",
    },
    {
        "keywords": ["orbit", "kepler", "satellite", "vis-viva", "gravity", "escape"],
        "law": "Vis-Viva & Kepler's Third Law",
        "domain": "Astrodynamics",
        "equation": "v^2 = GM\\left(\\frac{2}{r} - \\frac{1}{a}\\right), \\quad T^2 = \\frac{4\\pi^2}{GM}a^3",
        "axiom": "Conservation of specific orbital energy E = -GM/(2a) and angular momentum h = r x v.",
    },
    {
        "keywords": ["rocket", "tsiolkovsky", "propulsion", "impulse", "delta-v"],
        "law": "Tsiolkovsky Rocket Equation",
        "domain": "Aerospace",
        "equation": "\\Delta v = I_{sp} g_0 \\ln\\left(\\frac{m_0}{m_f}\\right), \\quad g_0 = 9.80665\\text{ m/s}^2",
        "axiom": "Momentum conservation for variable-mass reaction propulsion vehicles.",
    },
    {
        "keywords": ["quantum", "schrodinger", "tunneling", "wavefunction", "harmonic", "planck"],
        "law": "Time-Independent Schrödinger Equation & Tunneling",
        "domain": "Quantum Mechanics",
        "equation": "-\\frac{\\hbar^2}{2m}\\nabla^2\\psi + V(\\mathbf{r})\\psi = E\\psi, \\quad E_n = \\left(n + \\frac{1}{2}\\right)\\hbar\\omega",
        "axiom": "Wavefunction transmission through a finite barrier decays exponentially with barrier width and root height.",
    },
    {
        "keywords": ["fcc", "bcc", "hcp", "perovskite", "crystal", "miller", "bragg", "xrd", "eutectic", "lattice"],
        "law": "Bragg's Law & Crystallographic Packing",
        "domain": "Materials Science",
        "equation": "n\\lambda = 2 d_{hkl}\\sin\\theta, \\quad d_{hkl} = \\frac{a}{\\sqrt{h^2+k^2+l^2}}, \\quad \\text{APF}_{\\text{FCC}} = 0.74",
        "axiom": "FCC (Cu, Al, Au) has APF=0.74 and CN=12; BCC (Fe, W) has APF=0.68 and CN=8; Pb-Sn eutectic is at 183 C, 61.9 wt% Sn.",
    },
    {
        "keywords": ["dna", "helix", "protein", "membrane", "atp", "enzyme", "michaelis", "ion channel", "nernst"],
        "law": "Nernst Potential & Michaelis-Menten Kinetics",
        "domain": "Molecular Biology",
        "equation": "E_{\\text{ion}} = \\frac{RT}{zF}\\ln\\frac{[\\text{Ion}]_{\\text{out}}}{[\\text{Ion}]_{\\text{in}}}, \\quad v = \\frac{V_{\\max}[S]}{K_m + [S]}",
        "axiom": "B-DNA has 10.5 bp/turn and 3.4 nm pitch; A=T forms 2 H-bonds and G=C forms 3 H-bonds.",
    },
    {
        "keywords": ["saddle", "paraboloid", "gaussian", "curvature", "hessian", "curl", "divergence", "taylor", "stokes"],
        "law": "Gaussian Curvature, Vector Curl & Taylor Expansion",
        "domain": "Differential Geometry & Calculus",
        "equation": "K = \\frac{f_{xx}f_{yy} - f_{xy}^2}{(1 + f_x^2 + f_y^2)^2}, \\quad \\oint_{\\partial\\Sigma}\\mathbf{F}\\cdot d\\mathbf{r} = \\iint_{\\Sigma}(\\nabla\\times\\mathbf{F})\\cdot d\\mathbf{S}",
        "axiom": "Hyperbolic paraboloid z = x^2/a^2 - y^2/b^2 has negative Gaussian curvature K < 0 everywhere.",
    },
    {
        "keywords": ["ecg", "stemi", "sepsis", "embolism", "troponin", "lactate", "medical", "vitals", "cardiac"],
        "law": "Hemodynamic Oxygen Delivery & Mean Arterial Pressure",
        "domain": "Clinical Medicine",
        "equation": "\\text{MAP} = \\text{DBP} + \\frac{1}{3}(\\text{SBP} - \\text{DBP}), \\quad DO_2 = CO \\times (1.34 \\cdot \\text{Hb} \\cdot S_aO_2 + 0.003 P_aO_2)",
        "axiom": "STEMI exhibits ST-segment elevation in contiguous leads with elevated hs-cTnI; Septic Shock requires MAP >= 65 mmHg.",
    },
    {
        "keywords": ["gear", "propeller", "heatsink", "truss", "cad", "torsion", "beam"],
        "law": "Epicyclic Gear Ratio & Fin Heat Transfer",
        "domain": "Mechanical Engineering",
        "equation": "i = 1 + \\frac{Z_{\\text{ring}}}{Z_{\\text{sun}}}, \\quad q_{\\text{fin}} = \\sqrt{hPkA_c}(T_b - T_\\infty)\\tanh(mL)",
        "axiom": "Planetary gear train distributes torque across planet pinions; microchannel fins maximize convective surface area.",
    },
]


def _extract_math_expression(query: str) -> Optional[str]:
    """Extract a SymPy-evaluable expression from natural language STEM prompts."""
    q = query.strip()
    q_lower = q.lower()

    # Explicit SymPy function calls inside text
    direct_call = re.search(
        r"\b(integrate|diff|solve|simplify|expand|factor|limit|series|dsolve|Matrix)\s*\([^\n]+?\)",
        q
    )
    if direct_call:
        return direct_call.group(0).replace("^", "**")

    # Definite integral: integrate <expr> from <a> to <b>
    m_def = re.search(r"integrate\s+(.+?)\s+from\s+([^\s]+)\s+to\s+([^\s\?\.]+)", q_lower)
    if m_def:
        expr, a, b = m_def.groups()
        expr = expr.replace("dx", "").replace("^", "**").strip()
        a = "oo" if "inf" in a else a
        b = "oo" if "inf" in b else b
        return f"integrate({expr}, (x, {a}, {b}))"

    # Indefinite integral
    m_indef = re.search(r"(?:integrate|integral of)\s+([^\?\.\n]+)", q_lower)
    if m_indef:
        expr = m_indef.group(1).replace("dx", "").replace("^", "**").strip()
        if expr and len(expr) < 80:
            return f"integrate({expr}, x)"

    # Derivative
    m_diff = re.search(r"(?:derivative of|differentiate)\s+([^\?\.\n]+)", q_lower)
    if m_diff:
        expr = m_diff.group(1).replace("with respect to x", "").replace("^", "**").strip()
        if expr and len(expr) < 80:
            return f"diff({expr}, x)"

    # Solve algebraic equation
    m_solve = re.search(r"solve\s+([0-9a-zA-Z_\+\-\*\/\^\(\)\s=]+)", q_lower)
    if m_solve:
        target = m_solve.group(1).split(" and ")[0].replace("^", "**").strip()
        if "=" in target:
            lhs, rhs = target.split("=", 1)
            if lhs.strip() and rhs.strip():
                return f"solve(Eq({lhs.strip()}, {rhs.strip()}), x)"
        elif any(ch in target for ch in ("x", "+", "-", "*")):
            return f"solve({target}, x)"

    # Pure arithmetic / symbolic calculation
    m_calc = re.search(r"(?:calculate|evaluate|simplify)\s+([0-9x\+\-\*\/\^\(\)\.\s]+)", q_lower)
    if m_calc:
        target = m_calc.group(1).replace("^", "**").strip()
        if len(target) >= 3 and any(op in target for op in ("+", "-", "*", "/", "**")):
            return target

    return None


def enrich_stem_query(query: str) -> Dict[str, Any]:
    """
    Deterministic Neuro-Symbolic Enrichment:
    1. Evaluates exact symbolic/numerical math via SymPy AST Engine.
    2. Retrieves multi-hop physical laws, constants, and equations via KùzuDB + Curated STEM Graph.
    3. Returns structured badges and grounding context for the LLM or UI.
    """
    q = (query or "").strip()
    q_lower = q.lower()

    sympy_res = None
    if _SYMPY_ENGINE is not None:
        expr = _extract_math_expression(q)
        if expr:
            eval_out = _SYMPY_ENGINE.evaluate_expression(expr)
            if eval_out.get("success"):
                eval_out["expression"] = expr
                sympy_res = eval_out

    matched_axioms = []
    seen_laws = set()

    # Check Curated GraphRAG Knowledge Base (0.1ms, lock-free)
    for item in CURATED_GRAPH_AXIOMS:
        if any(kw in q_lower for kw in item["keywords"]):
            if item["law"] not in seen_laws:
                seen_laws.add(item["law"])
                matched_axioms.append({
                    "law": item["law"],
                    "topic": item["law"],
                    "domain": item["domain"],
                    "equation": item["equation"],
                    "axiom": item["axiom"],
                })

    # Also query KùzuDB if available and not locked
    global _STEM_GRAPH
    if len(matched_axioms) < 3 and q:
        try:
            if _STEM_GRAPH is None:
                from knowledge_graph.kuzu_stem_graph import VigyanSTEMGraph
                kuzu_path = "/home/hello/vigyan_masterpiece/knowledge_graph/db_store.db"
                if os.path.exists(os.path.dirname(kuzu_path)):
                    _STEM_GRAPH = VigyanSTEMGraph(db_path=kuzu_path)
            if _STEM_GRAPH is not None:
                words = [w for w in re.findall(r"\b[A-Za-z0-9_-]{3,}\b", q) if w.lower() not in {"what", "the", "and", "for", "with", "how", "derive", "explain", "plot", "simulate"}]
                ctx_str = _STEM_GRAPH.query_multihop_context(words[:6])
                if ctx_str:
                    for block in ctx_str.split("- [Graph "):
                        if not block.strip() or block.startswith("###"):
                            continue
                        first_line = block.splitlines()[0].strip()
                        law_title = first_line.split("]:", 1)[-1].strip()
                        if law_title and law_title not in seen_laws:
                            seen_laws.add(law_title)
                            eq_match = re.search(r"Equation:\s*(.+)", block)
                            ax_match = re.search(r"(?:Axiom|Definition|Properties):\s*(.+)", block)
                            matched_axioms.append({
                                "law": law_title,
                                "topic": law_title,
                                "domain": "KùzuDB GraphRAG",
                                "equation": eq_match.group(1).strip() if eq_match else "",
                                "axiom": ax_match.group(1).strip() if ax_match else block.replace("\n", " ")[:140],
                            })
        except Exception:
            pass

    prompt_injection = ""
    if sympy_res or matched_axioms:
        parts = ["[NEURO-SYMBOLIC VERIFIED GROUNDING • KùzuDB GraphRAG + SymPy AST]"]
        if sympy_res:
            parts.append(
                f"• SymPy AST Exact Evaluation: `{sympy_res.get('expression')}` = `{sympy_res.get('result')}` "
                f"(LaTeX: $${sympy_res.get('latex')}$$, Approx: {sympy_res.get('numeric_approx')})"
            )
        for ax in matched_axioms[:3]:
            parts.append(f"• [{ax['domain']}] {ax['law']}: $${ax['equation']}$$ — {ax['axiom']}")
        prompt_injection = "\n".join(parts)

    telemetry = get_system_telemetry()
    sympy_str = f"{sympy_res.get('expression')} = {sympy_res.get('result')}" if sympy_res else ""
    return {
        "query": q,
        "sympy": sympy_res,
        "sympy_verified": bool(sympy_res and sympy_res.get("success")),
        "sympy_result": sympy_str,
        "graph_axioms": matched_axioms[:4],
        "axioms": matched_axioms[:4],
        "prompt_injection": prompt_injection,
        "enriched_system_suffix": ("\n" + prompt_injection) if prompt_injection else "",
        "hybrid": telemetry["hybrid"],
    }


# ==============================================================================
# 3. EMBEDDED LOCAL SOVEREIGN AGENT & NEURO-SYMBOLIC BRIDGE (PORT 8085)
# ==============================================================================
class RAMGovernor:
    """Monitors system memory during model streaming inference.
    If RAM usage reaches or exceeds threshold_pct (default 88.0%),
    immediately triggers abort callback and issues keep_alive: 0 to Ollama.
    """
    def __init__(self, threshold_pct: float = 88.0, interval_sec: float = 0.1):
        self.threshold_pct = threshold_pct
        self.interval_sec = interval_sec
        self.tripped = False
        self.running = False
        self._thread = None
        self.peak_ram_pct = 0.0

    def start(self, on_trip_cb, active_model: str):
        self.tripped = False
        self.running = True
        self.peak_ram_pct = 0.0

        def _watchdog():
            consecutive_over = 0
            while self.running:
                try:
                    pct = psutil.virtual_memory().percent if psutil else 0.0
                    if pct > self.peak_ram_pct:
                        self.peak_ram_pct = pct
                    if pct >= self.threshold_pct:
                        consecutive_over += 1
                    else:
                        consecutive_over = 0

                    if consecutive_over >= 3 and not self.tripped:
                        self.tripped = True
                        print(f"⚠️ [RAM GOVERNOR] CRITICAL TRIPWIRE: RAM reached {pct:.1f}% >= {self.threshold_pct}% sustained. Aborting & evicting model {active_model}!")
                        try:
                            evict_req = urllib.request.Request(
                                "http://127.0.0.1:11434/api/generate",
                                headers={"Content-Type": "application/json"},
                                data=json.dumps({"model": active_model, "keep_alive": 0}).encode("utf-8"),
                            )
                            urllib.request.urlopen(evict_req, timeout=1.5)
                        except Exception:
                            pass
                        try:
                            on_trip_cb(pct)
                        except Exception:
                            pass
                        break
                except Exception:
                    pass
                time.sleep(self.interval_sec)

        self._thread = threading.Thread(target=_watchdog, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False


SAFE_READ_COMMANDS = {
    "ls", "dir", "cat", "head", "tail", "grep", "rg", "find", "pwd",
    "df", "free", "uptime", "uname", "whoami", "id", "which", "whereis",
    "ps", "top", "env", "echo", "date", "cal", "tree"
}

DANGEROUS_PATTERNS = [
    r"\brm\b", r"\bmv\b", r"\bcp\b", r"\bchmod\b", r"\bchown\b",
    r"\bdd\b", r"\bmkfs\b", r"\bkill\b", r"\bpkill\b", r"\bshutdown\b",
    r"\breboot\b", r"\bformat\b", r"\bsudo\b", r"\bsu\b", r"\bapt\b",
    r"\bdpkg\b", r"\bpip install\b", r"\bnpm install\b", r"\bsystemctl\b",
    r"\bcurl\b.*\|\s*(?:bash|sh)", r"\bwget\b.*\|\s*(?:bash|sh)",
    r">\s*/dev/", r">\s*/etc/", r">\s*/bin/", r">\s*/usr/"
]


def classify_command_safety(command: str) -> Dict[str, Any]:
    cmd_strip = command.strip()
    cmd_lower = cmd_strip.lower()
    for pat in DANGEROUS_PATTERNS:
        if re.search(pat, cmd_lower):
            return {
                "safe": False,
                "requires_approval": True,
                "reason": f"Modifies filesystem or system state ({pat})",
                "risk": "high" if ("rm" in pat or "sudo" in pat or "kill" in pat) else "medium"
            }
    first_word = cmd_lower.split()[0] if cmd_lower.split() else ""
    if first_word in SAFE_READ_COMMANDS:
        if ">" not in cmd_strip and "|" not in cmd_strip:
            return {"safe": True, "requires_approval": False, "reason": "Read-only inspection command", "risk": "low"}
    if cmd_lower.startswith("git ") and any(cmd_lower.startswith(f"git {sub}") for sub in ["status", "log", "branch", "diff", "show", "tag"]):
        return {"safe": True, "requires_approval": False, "reason": "Git read-only inspection", "risk": "low"}
    return {
        "safe": False,
        "requires_approval": True,
        "reason": "Arbitrary command execution",
        "risk": "medium"
    }


def execute_shell_command(command: str, confirmed: bool = False, cwd: Optional[str] = None) -> Dict[str, Any]:
    safety = classify_command_safety(command)
    if safety["requires_approval"] and not confirmed:
        return {
            "success": False,
            "status": "requires_approval",
            "command": command,
            "risk": safety["risk"],
            "reason": safety["reason"],
            "cwd": cwd or os.getcwd()
        }
    work_dir = cwd if (cwd and os.path.isdir(cwd)) else os.getcwd()
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=work_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15.0
        )
        return {
            "success": proc.returncode == 0,
            "status": "executed",
            "command": command,
            "returncode": proc.returncode,
            "stdout": proc.stdout[:10000],
            "stderr": proc.stderr[:5000],
            "cwd": work_dir
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "status": "timeout",
            "command": command,
            "returncode": -1,
            "stdout": "",
            "stderr": "Command execution timed out after 15 seconds.",
            "cwd": work_dir
        }
    except Exception as exc:
        return {
            "success": False,
            "status": "error",
            "command": command,
            "returncode": -1,
            "stdout": "",
            "stderr": str(exc),
            "cwd": work_dir
        }


def select_cascade_model(requested_model: str, query: str) -> Dict[str, Any]:
    """Sovereign Vigyan AI execution router locked to Vigyan AI 1.5B Quad Master."""
    return {
        "tier": 1,
        "model": "vigyan:1.5b",
        "downgraded": False,
        "reason": "Vigyan AI 1.5B Quad Master (Sovereign ChatML architecture)"
    }


# ==============================================================================
# 3.1 VIGYAN AI SOVEREIGN MODEL REGISTRY & DOWNLOAD MANAGER
# ==============================================================================
MODELS_CATALOG = {
    "vigyan:1.5b": {
        "name": "Vigyan AI 1.5B Quad Master",
        "tag": "vigyan:1.5b",
        "size_bytes": 1181116006,
        "size_formatted": "1.1 GB",
        "recommended_ram": "2 GB+ RAM (Ultra-fast edge inference, zero latency)",
        "description": "Proprietary high-velocity STEM & math quad-master model with instant responses, ChatML formatting, and zero-hallucination calculus.",
        "dest_filename": "vigyan-1.5b-quad-master-q4_k_m.gguf",
        "hf_url": "https://github.com/shreyansh001boy-tech/vigyan-desktop-releases/releases/download/v2.9.0-beta/vigyan-1.5b-quad-master-q4_k_m.gguf",
        "local_candidates": [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "vigyan-1.5b-quad-master-q4_k_m.gguf"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "vigyan-1.5b-quad-master-q4_k_m.gguf"),
            os.path.expanduser("~/.vigyan/models/vigyan-1.5b-quad-master-q4_k_m.gguf"),
            os.path.expanduser("~/models/vigyan-1.5b-quad-master-q4_k_m.gguf"),
            os.path.expanduser("~/Downloads/vigyan-1.5b-quad-master-q4_k_m.gguf")
        ],
        "template": """{{- if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{- range .Messages }}<|im_start|>{{ .Role }}
{{ .Content }}<|im_end|>
{{ end }}<|im_start|>assistant
""",
        "stop": ["<|im_start|>", "<|im_end|>", "<|endoftext|>"]
    }
}


def ensure_vigyan_1_5b_registered() -> bool:
    """Autonomous verifier and auto-repair for Vigyan AI 1.5B Quad Master in Ollama."""
    try:
        check = subprocess.run(["ollama", "show", "vigyan:1.5b"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2.0)
        if check.returncode == 0:
            return True
    except Exception:
        pass

    target_dir = os.path.expanduser("~/.vigyan/models")
    os.makedirs(target_dir, exist_ok=True)
    gguf_path = os.path.join(target_dir, "vigyan-1.5b-quad-master-q4_k_m.gguf")

    if not os.path.isfile(gguf_path) or os.path.getsize(gguf_path) < 500_000_000:
        # Check bundled / local candidate paths first
        candidates = MODELS_CATALOG.get("vigyan:1.5b", {}).get("local_candidates", [])
        found_local = None
        for cand in candidates:
            if cand and os.path.isfile(cand) and os.path.getsize(cand) >= 500_000_000:
                found_local = cand
                break

        if found_local:
            print(f"[INFO] Discovered bundled sovereign model weights at: {found_local}", file=sys.stderr)
            if os.path.abspath(found_local) != os.path.abspath(gguf_path):
                try:
                    import shutil
                    print("[INFO] Importing sovereign model into ~/.vigyan/models/...", file=sys.stderr)
                    shutil.copy2(found_local, gguf_path)
                except Exception:
                    gguf_path = found_local
        else:
            token_path = os.path.expanduser("~/.cache/huggingface/token")
            hf_token = ""
            if os.path.isfile(token_path):
                try:
                    with open(token_path, "r", encoding="utf-8") as f:
                        hf_token = f.read().strip()
                except Exception:
                    pass
            try:
                from huggingface_hub import hf_hub_download
                print("[INFO] Auto-repair: Downloading vigyan-1.5b-quad-master from Hugging Face...", file=sys.stderr)
                hf_hub_download(
                    repo_id="shreyansh12183/vigyan-1.5b-quad-master",
                    filename="vigyan-1.5b-quad-master-q4_k_m.gguf",
                    token=hf_token or None,
                    local_dir=target_dir
                )
            except Exception as e:
                print(f"[WARN] HF auto-repair download error: {e}", file=sys.stderr)
                return False

    modelfile_path = os.path.join(target_dir, "Modelfile.vigyan-1.5b")
    modelfile_content = (
        f"FROM {gguf_path}\n"
        'TEMPLATE """{{- if .System }}<|im_start|>system\n'
        "{{ .System }}<|im_end|>\n"
        '{{ end }}{{- range .Messages }}<|im_start|>{{ .Role }}\n'
        "{{ .Content }}<|im_end|>\n"
        '{{ end }}<|im_start|>assistant\n'
        '"""\n'
        'SYSTEM """You are Vigyan AI 1.5B Quad Master, a sovereign STEM, mathematical reasoning, physics simulation, and coding intelligence system architected and trained by Shreyansh Singh. Solve problems with rigorous mathematical proofs, clean LaTeX ($$...$$), and concise explanations. Be direct, authoritative, and professional. You operate with 100% offline edge privacy and zero corporate API dependency."""\n'
        'PARAMETER stop "<|im_start|>"\n'
        'PARAMETER stop "<|im_end|>"\n'
        'PARAMETER stop "<|endoftext|>"\n'
        'PARAMETER stop "User:"\n'
        'PARAMETER stop "\\n\\nUser"\n'
        'PARAMETER stop "Human:"\n'
        "PARAMETER num_gpu 0\n"
        "PARAMETER temperature 0.2\n"
        "PARAMETER top_p 0.95\n"
        "PARAMETER top_k 40\n"
        "PARAMETER num_ctx 2048\n"
    )
    with open(modelfile_path, "w", encoding="utf-8") as mf:
        mf.write(modelfile_content)

    try:
        print("[INFO] Auto-repair: Registering vigyan:1.5b into Ollama...", file=sys.stderr)
        res = subprocess.run(["ollama", "create", "vigyan:1.5b", "-f", modelfile_path], capture_output=True, timeout=120)
        return res.returncode == 0
    except Exception as e:
        print(f"[WARN] Ollama registration error: {e}", file=sys.stderr)
        return False


class ModelDownloadManager:
    """Resumable chunked model downloader with speed tracking and Ollama auto-registration."""
    def __init__(self):
        self.active_downloads: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get_status(self, tag: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            if tag:
                return self.active_downloads.get(tag, {"status": "idle"})
            return dict(self.active_downloads)

    def start_download(self, tag: str) -> Dict[str, Any]:
        info = MODELS_CATALOG.get(tag)
        if not info:
            return {"success": False, "error": f"Unknown model: {tag}"}

        with self._lock:
            if tag in self.active_downloads and self.active_downloads[tag]["status"] in ("downloading", "registering"):
                return {"success": True, "message": "Already downloading", "status": self.active_downloads[tag]}
            self.active_downloads[tag] = {
                "tag": tag,
                "name": info["name"],
                "status": "starting",
                "progress_pct": 0.0,
                "downloaded_bytes": 0,
                "total_bytes": info["size_bytes"],
                "speed_mbps": 0.0,
                "error": None
            }

        # 0. Check if model already exists in Ollama
        try:
            check_proc = subprocess.run(["ollama", "show", tag], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=0.8)
            if check_proc.returncode == 0:
                with self._lock:
                    self.active_downloads[tag] = {
                        "tag": tag,
                        "name": info["name"],
                        "status": "ready",
                        "progress_pct": 100.0,
                        "downloaded_bytes": info["size_bytes"],
                        "total_bytes": info["size_bytes"],
                        "speed_mbps": 0.0,
                        "error": None
                    }
                return {"success": True, "message": f"{tag} is already installed in Ollama", "status": "ready"}
        except Exception:
            pass

        # Check local candidate files first (instant local import)
        for cand in info.get("local_candidates", []):
            if os.path.isfile(cand) and os.path.getsize(cand) > 100_000_000:
                def _instant_register():
                    with self._lock:
                        self.active_downloads[tag]["status"] = "registering"
                        self.active_downloads[tag]["progress_pct"] = 100.0
                    target_dir = os.path.expanduser("~/.vigyan/models")
                    os.makedirs(target_dir, exist_ok=True)
                    dest_file = cand
                    # Register into Ollama directly
                    modelfile_path = os.path.join(target_dir, f"Modelfile.{tag.replace(':', '_')}")
                    with open(modelfile_path, "w", encoding="utf-8") as mf:
                        mf.write(f"FROM {dest_file}\nTEMPLATE \"\"\"{info['template']}\"\"\"\n")
                        for s in info.get("stop", []):
                            mf.write(f"PARAMETER stop \"{s}\"\n")
                    subprocess.run(["ollama", "create", tag, "-f", modelfile_path], check=False)
                    with self._lock:
                        self.active_downloads[tag]["status"] = "ready"
                threading.Thread(target=_instant_register, daemon=True).start()
                return {"success": True, "message": "Found local weights, registering into Ollama...", "status": "registering"}

        # Background resumable download thread
        def _download_thread():
            target_dir = os.path.expanduser("~/.vigyan/models")
            os.makedirs(target_dir, exist_ok=True)
            dest_file = os.path.join(target_dir, info["dest_filename"])
            part_file = dest_file + ".part"

            existing_bytes = os.path.getsize(part_file) if os.path.exists(part_file) else 0
            headers = {"User-Agent": "Vigyan-Desktop-Sovereign-Downloader/1.0"}
            if existing_bytes > 0:
                headers["Range"] = f"bytes={existing_bytes}-"

            try:
                with self._lock:
                    self.active_downloads[tag]["status"] = "downloading"
                    self.active_downloads[tag]["downloaded_bytes"] = existing_bytes

                req = urllib.request.Request(info["hf_url"], headers=headers)
                start_time = time.time()
                bytes_this_session = 0

                with urllib.request.urlopen(req, timeout=30) as resp:
                    total = info["size_bytes"]
                    cr = resp.headers.get("Content-Range")
                    if cr and "/" in cr:
                        try:
                            total = int(cr.split("/")[-1])
                        except Exception:
                            pass
                    elif resp.headers.get("Content-Length") and existing_bytes == 0:
                        total = int(resp.headers.get("Content-Length"))

                    mode = "ab" if existing_bytes > 0 else "wb"
                    with open(part_file, mode) as f:
                        while True:
                            with self._lock:
                                if self.active_downloads.get(tag, {}).get("status") == "cancelled":
                                    return
                            chunk = resp.read(1024 * 256)
                            if not chunk:
                                break
                            f.write(chunk)
                            bytes_this_session += len(chunk)
                            current_total = existing_bytes + bytes_this_session
                            elapsed = max(0.1, time.time() - start_time)
                            speed_mbps = (bytes_this_session / (1024 * 1024)) / elapsed
                            pct = min(99.0, round((current_total / max(1, total)) * 100, 1))

                            with self._lock:
                                self.active_downloads[tag]["downloaded_bytes"] = current_total
                                self.active_downloads[tag]["total_bytes"] = total
                                self.active_downloads[tag]["progress_pct"] = pct
                                self.active_downloads[tag]["speed_mbps"] = round(speed_mbps, 1)

                os.rename(part_file, dest_file)
                with self._lock:
                    self.active_downloads[tag]["status"] = "registering"
                    self.active_downloads[tag]["progress_pct"] = 100.0

                modelfile_path = os.path.join(target_dir, f"Modelfile.{tag.replace(':', '_')}")
                with open(modelfile_path, "w", encoding="utf-8") as mf:
                    mf.write(f"FROM {dest_file}\nTEMPLATE \"\"\"{info['template']}\"\"\"\n")
                    for s in info.get("stop", []):
                        mf.write(f"PARAMETER stop \"{s}\"\n")
                subprocess.run(["ollama", "create", tag, "-f", modelfile_path], check=False)

                with self._lock:
                    self.active_downloads[tag]["status"] = "ready"

            except Exception as exc:
                with self._lock:
                    self.active_downloads[tag]["status"] = "error"
                    self.active_downloads[tag]["error"] = str(exc)

        threading.Thread(target=_download_thread, daemon=True).start()
        return {"success": True, "message": "Download started", "tag": tag}

    def cancel_download(self, tag: str) -> bool:
        with self._lock:
            if tag in self.active_downloads:
                self.active_downloads[tag]["status"] = "cancelled"
                return True
            return False


_DOWNLOAD_MGR = ModelDownloadManager()


# ==============================================================================
# 3.2 LOCAL WORKSPACE FILE AGENT TOOLS
# ==============================================================================
def list_workspace_dir(path: str = ".") -> Dict[str, Any]:
    safe_path = os.path.abspath(path)
    if not os.path.isdir(safe_path):
        return {"success": False, "error": f"Directory not found: {path}"}
    items = []
    try:
        for entry in os.scandir(safe_path):
            try:
                stat = entry.stat()
                items.append({
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "size": stat.st_size if not entry.is_dir() else 0,
                    "mtime": stat.st_mtime
                })
            except Exception:
                pass
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return {"success": True, "path": safe_path, "items": items[:100]}
    except Exception as e:
        return {"success": False, "error": str(e)}


def read_workspace_file(path: str, start_line: int = 1, end_line: int = 200) -> Dict[str, Any]:
    safe_path = os.path.abspath(path)
    if not os.path.isfile(safe_path):
        return {"success": False, "error": f"File not found: {path}"}
    try:
        with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        total_lines = len(lines)
        s = max(1, start_line)
        e = min(total_lines, max(s, end_line))
        chunk = "".join(lines[s-1:e])
        return {
            "success": True,
            "path": safe_path,
            "total_lines": total_lines,
            "start_line": s,
            "end_line": e,
            "content": chunk
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def write_workspace_file(path: str, content: str, overwrite: bool = False) -> Dict[str, Any]:
    safe_path = os.path.abspath(path)
    if os.path.exists(safe_path) and not overwrite:
        return {
            "success": False,
            "status": "requires_approval",
            "reason": f"File '{os.path.basename(path)}' already exists. Overwrite requires user confirmation.",
            "path": safe_path,
            "command": f"write_file({os.path.basename(path)})"
        }
    try:
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "status": "written", "path": safe_path, "bytes": len(content.encode("utf-8"))}
    except Exception as e:
        return {"success": False, "error": str(e)}


def grep_workspace_files(query: str, path: str = ".") -> Dict[str, Any]:
    safe_path = os.path.abspath(path)
    matches = []
    # Fast-path: use grep binary on Unix/Linux if available
    if shutil.which("grep") and not sys.platform.startswith("win32"):
        try:
            proc = subprocess.run(
                ["grep", "-rnI", "--exclude-dir=.git", "--exclude-dir=node_modules", "--exclude-dir=__pycache__", "-m", "50", query, safe_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=8.0
            )
            for line in proc.stdout.splitlines()[:50]:
                parts = line.split(":", 2)
                if len(parts) >= 3:
                    rel = os.path.relpath(parts[0], safe_path)
                    matches.append({"file": rel, "line": int(parts[1]) if parts[1].isdigit() else 0, "text": parts[2].strip()})
            return {"success": True, "query": query, "matches": matches}
        except Exception:
            pass

    # Universal cross-platform pure-Python search fallback (Windows / macOS / minimal environments)
    try:
        q_lower = query.lower()
        count = 0
        skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "dist", "build"}
        for root, dirs, files in os.walk(safe_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for line_no, line in enumerate(f, 1):
                            if q_lower in line.lower():
                                rel = os.path.relpath(fpath, safe_path)
                                matches.append({"file": rel, "line": line_no, "text": line.strip()})
                                count += 1
                                if count >= 50:
                                    break
                except Exception:
                    pass
                if count >= 50:
                    break
            if count >= 50:
                break
        return {"success": True, "query": query, "matches": matches}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==============================================================================
# 3.2.1 SOVEREIGN AGENTIC STEM & SCIENTIFIC COMPUTING TOOLS
# ==============================================================================
_SAFE_MATH_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name,
    ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div,
    ast.Pow, ast.USub, ast.UAdd, ast.Mod, ast.FloorDiv, ast.Load
)

_SAFE_MATH_ENV = {
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
    "exp": math.exp, "log": math.log, "log10": math.log10, "log2": math.log2,
    "ln": math.log, "sqrt": math.sqrt, "abs": abs,
    "pi": math.pi, "e": math.e, "tau": math.tau,
}


def evaluate_plot(
    expression: str,
    x_min: float = -10.0,
    x_max: float = 10.0,
    points: int = 200,
    title: str = "",
    x_label: str = "x",
    y_label: str = "y"
) -> Dict[str, Any]:
    """Safely evaluates a continuous mathematical function f(x) and returns high-resolution (x, y) plot traces."""
    clean_expr = expression.strip()
    if clean_expr.lower().startswith("f(x) ="):
        clean_expr = clean_expr[6:].strip()
    elif clean_expr.lower().startswith("f(x)="):
        clean_expr = clean_expr[5:].strip()
    elif clean_expr.lower().startswith("y ="):
        clean_expr = clean_expr[3:].strip()
    elif clean_expr.lower().startswith("y="):
        clean_expr = clean_expr[2:].strip()

    clean_expr = clean_expr.replace("^", "**").strip()
    try:
        tree = ast.parse(clean_expr, mode="eval")
    except Exception:
        # Try normalizing implicit multiplication e.g. 0.15x -> 0.15*x, )cos -> )*cos
        norm = re.sub(r"(\d+)([a-zA-Z\(])", r"\1*\2", clean_expr)
        norm = re.sub(r"\)([a-zA-Z\(])", r")*\1", norm)
        try:
            tree = ast.parse(norm, mode="eval")
            clean_expr = norm
        except Exception as exc:
            return {"tool": "plot_function", "success": False, "error": f"Mathematical parse error: {exc}"}

    try:
        for node in ast.walk(tree):
            if not isinstance(node, _SAFE_MATH_NODES):
                return {"tool": "plot_function", "success": False, "error": f"Disallowed mathematical syntax: {type(node).__name__}"}
            if isinstance(node, ast.Name) and node.id != "x" and node.id not in _SAFE_MATH_ENV:
                return {"tool": "plot_function", "success": False, "error": f"Unknown or disallowed symbol: {node.id}"}
        compiled_code = compile(tree, "<plot_math>", "eval")
    except Exception as exc:
        return {"tool": "plot_function", "success": False, "error": f"Mathematical parse error: {exc}"}

    x_min = float(x_min)
    x_max = float(x_max)
    points = max(10, min(1000, int(points)))
    step = (x_max - x_min) / max(1, points - 1)
    
    x_vals: List[float] = []
    y_vals: List[Optional[float]] = []
    env = dict(_SAFE_MATH_ENV)

    for i in range(points):
        x = x_min + i * step
        env["x"] = x
        try:
            val = eval(compiled_code, {"__builtins__": {}}, env)
            if math.isnan(val) or math.isinf(val):
                y_vals.append(None)
            else:
                y_vals.append(round(float(val), 5))
        except Exception:
            y_vals.append(None)
        x_vals.append(round(x, 4))

    return {
        "tool": "plot_function",
        "success": True,
        "expression": expression,
        "title": title or f"f(x) = {expression}",
        "x_label": x_label,
        "y_label": y_label,
        "x_range": [x_min, x_max],
        "points": points,
        "plot": {
            "title": title or f"f(x) = {expression}",
            "x_label": x_label,
            "y_label": y_label,
            "traces": [
                {
                    "x": x_vals,
                    "y": y_vals,
                    "name": expression,
                    "mode": "lines",
                    "line": {"color": "#38bdf8", "width": 2}
                }
            ]
        }
    }


def calc_circuit(circuit_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Calculates electrical engineering circuits (RC Filter, RLC Resonator, 555 Timer) with real formulas & curves."""
    ctype = (circuit_type or "rc_filter").lower()
    
    # 1. RC FILTER (Lowpass / Highpass)
    if ctype in ("rc_filter", "rc", "filter"):
        try:
            r = float(params.get("r", 10000.0))
            c = float(params.get("c", 1e-7))
            ftype = str(params.get("filter_type", "lowpass")).lower()
            if r <= 0 or c <= 0:
                return {"tool": "circuit_calc", "success": False, "error": "Resistance and capacitance must be positive."}
            
            fc = 1.0 / (2.0 * math.pi * r * c)
            tau = r * c
            
            # Bode plot frequency response (60 log-spaced points from 0.01*fc to 100*fc)
            freqs = []
            mags_db = []
            for i in range(60):
                exp = -2.0 + (4.0 * i / 59.0)
                f = fc * (10.0 ** exp)
                ratio = f / fc
                freqs.append(round(f, 2))
                if ftype == "highpass":
                    mag = 20.0 * math.log10(ratio / math.sqrt(1.0 + ratio**2))
                else:
                    mag = -10.0 * math.log10(1.0 + ratio**2)
                mags_db.append(round(mag, 2))
                
            return {
                "tool": "circuit_calc",
                "success": True,
                "circuit_type": f"RC {ftype.capitalize()} Filter",
                "metrics": [
                    {"label": "Cutoff Frequency (fc)", "value": f"{fc:.2f} Hz"},
                    {"label": "Time Constant (τ)", "value": f"{tau * 1e3:.2f} ms"},
                    {"label": "Resistance (R)", "value": f"{r:g} Ω"},
                    {"label": "Capacitance (C)", "value": f"{c:g} F"}
                ],
                "formula_latex": r"f_c = \frac{1}{2\pi R C}, \quad \tau = R \cdot C",
                "plot": {
                    "title": f"RC {ftype.capitalize()} Bode Magnitude (fc = {fc:.1f} Hz)",
                    "x_label": "Frequency (Hz, log scale)",
                    "y_label": "Magnitude (dB)",
                    "x_log": True,
                    "traces": [
                        {"x": freqs, "y": mags_db, "name": "Magnitude (dB)", "line": {"color": "#38bdf8", "width": 2}}
                    ]
                }
            }
        except Exception as e:
            return {"tool": "circuit_calc", "success": False, "error": str(e)}

    # 2. RLC RESONATOR (Series / Parallel)
    elif ctype in ("rlc_resonance", "rlc", "resonance"):
        try:
            r = float(params.get("r", 10.0))
            l = float(params.get("l", 0.01))
            c = float(params.get("c", 1e-6))
            cfg = str(params.get("config", "series")).lower()
            if r <= 0 or l <= 0 or c <= 0:
                return {"tool": "circuit_calc", "success": False, "error": "R, L, and C must be positive."}

            f0 = 1.0 / (2.0 * math.pi * math.sqrt(l * c))
            omega0 = 2.0 * math.pi * f0
            q = (1.0 / r) * math.sqrt(l / c) if cfg != "parallel" else r * math.sqrt(c / l)
            bw = f0 / q if q > 0 else 0.0
            zeta = 1.0 / (2.0 * q) if q > 0 else 0.0

            freqs = []
            resp_mag = []
            for i in range(80):
                f = f0 * (0.2 + 1.8 * (i / 79.0))
                w = 2.0 * math.pi * f
                ratio = w / omega0
                denom = math.sqrt((1.0 - ratio**2)**2 + (ratio / q)**2)
                mag = (1.0 / denom) if denom > 0 else 0.0
                freqs.append(round(f, 2))
                resp_mag.append(round(mag, 3))

            return {
                "tool": "circuit_calc",
                "success": True,
                "circuit_type": f"RLC {cfg.capitalize()} Resonator",
                "metrics": [
                    {"label": "Resonant Frequency (f0)", "value": f"{f0:.2f} Hz"},
                    {"label": "Quality Factor (Q)", "value": f"{q:.2f}"},
                    {"label": "Bandwidth (BW)", "value": f"{bw:.2f} Hz"},
                    {"label": "Damping Factor (ζ)", "value": f"{zeta:.4f}"},
                    {"label": "Inductance (L)", "value": f"{l:g} H"}
                ],
                "formula_latex": r"f_0 = \frac{1}{2\pi\sqrt{LC}}, \quad Q = \frac{1}{R}\sqrt{\frac{L}{C}}, \quad BW = \frac{f_0}{Q}",
                "plot": {
                    "title": f"RLC Resonance Curve (f0 = {f0:.1f} Hz, Q = {q:.1f})",
                    "x_label": "Frequency (Hz)",
                    "y_label": "Normalized Gain |H(f)|",
                    "traces": [
                        {"x": freqs, "y": resp_mag, "name": "Gain |H(f)|", "line": {"color": "#10b981", "width": 2}}
                    ]
                }
            }
        except Exception as e:
            return {"tool": "circuit_calc", "success": False, "error": str(e)}

    # 3. 555 ASTABLE TIMER
    elif ctype in ("555_timer", "555", "astable"):
        try:
            r1 = float(params.get("r1", 10000.0))
            r2 = float(params.get("r2", 47000.0))
            c = float(params.get("c", 1e-6))
            if r1 <= 0 or r2 <= 0 or c <= 0:
                return {"tool": "circuit_calc", "success": False, "error": "R1, R2, and C must be positive."}

            th = 0.69315 * (r1 + r2) * c
            tl = 0.69315 * r2 * c
            t_period = th + tl
            freq = 1.0 / t_period if t_period > 0 else 0.0
            duty = ((r1 + r2) / (r1 + 2.0 * r2)) * 100.0

            ts = []
            v_out = []
            pts = 90
            for i in range(pts):
                t = (i / (pts - 1)) * (3.0 * t_period)
                cycle_t = t % t_period
                ts.append(round(t * 1e3, 2))  # ms
                v_out.append(5.0 if cycle_t < th else 0.0)

            return {
                "tool": "circuit_calc",
                "success": True,
                "circuit_type": "NE555 Astable Multivibrator",
                "metrics": [
                    {"label": "Frequency (f)", "value": f"{freq:.2f} Hz"},
                    {"label": "Duty Cycle (D)", "value": f"{duty:.1f}%"},
                    {"label": "Period (T)", "value": f"{t_period * 1e3:.2f} ms"},
                    {"label": "High Time (t_high)", "value": f"{th * 1e3:.2f} ms"},
                    {"label": "Low Time (t_low)", "value": f"{tl * 1e3:.2f} ms"}
                ],
                "formula_latex": r"f = \frac{1.44}{(R_1 + 2R_2)C}, \quad D = \frac{R_1+R_2}{R_1+2R_2}\times 100\%",
                "plot": {
                    "title": f"555 Timer Square Wave (f = {freq:.1f} Hz, D = {duty:.1f}%)",
                    "x_label": "Time (ms)",
                    "y_label": "Output Voltage (V)",
                    "traces": [
                        {"x": ts, "y": v_out, "name": "V_out (5V Logic)", "line": {"color": "#a855f7", "width": 2, "shape": "hv"}}
                    ]
                }
            }
        except Exception as e:
            return {"tool": "circuit_calc", "success": False, "error": str(e)}

    return {"tool": "circuit_calc", "success": False, "error": f"Unknown circuit type: '{ctype}' (supported: rc_filter, rlc_resonance, 555_timer)"}


def calc_physics(sim_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Calculates orbital mechanics & projectile kinematics with Keplerian trajectory generation."""
    stype = (sim_type or "kepler_orbit").lower()

    # 1. KEPLERIAN ORBIT
    if stype in ("kepler_orbit", "orbit", "kepler", "satellite"):
        try:
            a = float(params.get("semi_major_axis_km") or params.get("a") or 7000.0)
            e = float(params.get("eccentricity") or params.get("e") or 0.05)
            e = max(0.0, min(0.95, e))
            body = str(params.get("body") or "earth").lower()
            mu_map = {
                "earth": 398600.4418,
                "sun": 1.32712440018e11,
                "moon": 4902.8,
                "mars": 42828.3
            }
            mu = float(params.get("mu") or mu_map.get(body, 398600.4418))

            period_sec = 2.0 * math.pi * math.sqrt((a**3) / mu)
            rp = a * (1.0 - e)
            ra = a * (1.0 + e)
            vp = math.sqrt(mu * (1.0 + e) / (a * (1.0 - e)))
            va = math.sqrt(mu * (1.0 - e) / (a * (1.0 + e)))

            # Trajectory: 360 points around focus (0, 0)
            xs = []
            ys = []
            p = a * (1.0 - e**2)
            for deg in range(361):
                theta = math.radians(deg)
                r = p / (1.0 + e * math.cos(theta))
                xs.append(round(r * math.cos(theta), 2))
                ys.append(round(r * math.sin(theta), 2))

            return {
                "tool": "physics_sim",
                "success": True,
                "sim_type": f"Keplerian Orbit ({body.capitalize()})",
                "metrics": [
                    {"label": "Orbital Period (T)", "value": f"{period_sec / 60.0:.2f} min ({period_sec / 3600.0:.2f} h)"},
                    {"label": "Periapsis (rp)", "value": f"{rp:,.1f} km"},
                    {"label": "Apoapsis (ra)", "value": f"{ra:,.1f} km"},
                    {"label": "Periapsis Speed (vp)", "value": f"{vp:.3f} km/s"},
                    {"label": "Apoapsis Speed (va)", "value": f"{va:.3f} km/s"},
                    {"label": "Semi-major Axis (a)", "value": f"{a:,.1f} km"},
                    {"label": "Eccentricity (e)", "value": f"{e:.4f}"}
                ],
                "formula_latex": r"T = 2\pi\sqrt{\frac{a^3}{\mu}}, \quad r(\theta) = \frac{a(1-e^2)}{1+e\cos\theta}, \quad v_p = \sqrt{\frac{\mu(1+e)}{a(1-e)}}",
                "plot": {
                    "title": f"Keplerian 2D Orbit ({body.capitalize()}, a={a:,.0f}km, e={e:.2f})",
                    "x_label": "X Distance (km)",
                    "y_label": "Y Distance (km)",
                    "traces": [
                        {"x": xs, "y": ys, "name": "Trajectory", "line": {"color": "#38bdf8", "width": 2}},
                        {"x": [0], "y": [0], "name": body.capitalize(), "mode": "markers", "marker": {"size": 12, "color": "#fbbf24"}}
                    ]
                }
            }
        except Exception as e:
            return {"tool": "physics_sim", "success": False, "error": str(e)}

    # 2. BALLISTIC PROJECTILE KINEMATICS
    elif stype in ("projectile", "ballistics", "kinematics"):
        try:
            v0 = float(params.get("velocity") or params.get("v0") or 50.0)
            angle = float(params.get("angle_deg") or params.get("theta") or 45.0)
            h0 = float(params.get("height") or params.get("h0") or 0.0)
            g = float(params.get("gravity") or params.get("g") or 9.80665)

            rad = math.radians(angle)
            v0x = v0 * math.cos(rad)
            v0y = v0 * math.sin(rad)

            disc = v0y**2 + 2.0 * g * h0
            t_flight = (v0y + math.sqrt(max(0.0, disc))) / g
            h_max = h0 + (v0y**2) / (2.0 * g)
            r_max = v0x * t_flight

            xs = []
            ys = []
            pts = 80
            for i in range(pts):
                t = (i / (pts - 1)) * t_flight
                x = v0x * t
                y = h0 + v0y * t - 0.5 * g * (t**2)
                xs.append(round(x, 2))
                ys.append(round(max(0.0, y), 2))

            return {
                "tool": "physics_sim",
                "success": True,
                "sim_type": "Ballistic Projectile Kinematics",
                "metrics": [
                    {"label": "Flight Time (t_f)", "value": f"{t_flight:.2f} s"},
                    {"label": "Maximum Altitude (H)", "value": f"{h_max:.2f} m"},
                    {"label": "Horizontal Range (R)", "value": f"{r_max:.2f} m"},
                    {"label": "Launch Velocity (v0)", "value": f"{v0:.1f} m/s"},
                    {"label": "Launch Angle (θ)", "value": f"{angle:.1f}°"}
                ],
                "formula_latex": r"t_f = \frac{v_0\sin\theta + \sqrt{(v_0\sin\theta)^2 + 2gh_0}}{g}, \quad R = v_0\cos\theta \cdot t_f",
                "plot": {
                    "title": f"Projectile Trajectory (v0 = {v0}m/s, θ = {angle}°, Range = {r_max:.1f}m)",
                    "x_label": "Downrange Distance (m)",
                    "y_label": "Altitude (m)",
                    "traces": [
                        {"x": xs, "y": ys, "name": "Trajectory", "line": {"color": "#ec4899", "width": 2}}
                    ]
                }
            }
        except Exception as e:
            return {"tool": "physics_sim", "success": False, "error": str(e)}

    return {"tool": "physics_sim", "success": False, "error": f"Unknown sim type: '{stype}' (supported: kepler_orbit, projectile)"}


def compress_conversation_history(messages: List[Dict[str, str]], max_tokens_est: int = 650) -> List[Dict[str, str]]:
    """
    Sliding Window + Micro-Summary Compressor.
    Preserves system axioms & original user goal, condenses intermediate turns into
    a compact bulleted memory summary, and streams the latest 4 turns verbatim.
    Prevents overflowing the 1024-token budget on long sessions.
    """
    if not messages or len(messages) <= 5:
        return messages

    total_chars = sum(len(m.get("content", "")) for m in messages)
    if total_chars < max_tokens_est * 4:
        return messages

    system_msg = messages[0] if messages[0].get("role") == "system" else None
    rest = messages[1:] if system_msg else messages

    if len(rest) <= 4:
        return messages

    initial_turn = rest[0]
    latest_turns = rest[-4:]
    middle_turns = rest[1:-4]

    bullets = []
    for m in middle_turns:
        role = m.get("role", "user")
        snippet = m.get("content", "").strip()[:70].replace("\n", " ")
        if snippet:
            bullets.append(f"{role.capitalize()}: {snippet}...")

    summary_text = "[Conversation Memory Summary]: " + "; ".join(bullets[:5])
    summary_msg = {"role": "system", "content": summary_text}

    compressed = []
    if system_msg:
        compressed.append(system_msg)
    compressed.append(initial_turn)
    compressed.append(summary_msg)
    compressed.extend(latest_turns)
    return compressed


def check_github_update() -> Dict[str, Any]:
    """Check GitHub releases for the latest version tag."""
    repo = "shreyansh001boy-tech/vigyan-pro-desktop"
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Vigyan-Pro-Desktop"})
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                tag = data.get("tag_name", "").lstrip("v")
                body = data.get("body", "Performance enhancements and bug fixes.")
                assets = data.get("assets", [])
                hotpatch_url = next((a["browser_download_url"] for a in assets if "hotpatch" in a["name"].lower() or "src" in a["name"].lower()), "")
                is_newer = False
                if tag and tag != __version__:
                    is_newer = tag > __version__
                return {
                    "current_version": __version__,
                    "latest_version": tag or __version__,
                    "update_available": is_newer,
                    "release_notes": body[:200],
                    "hotpatch_url": hotpatch_url
                }
    except Exception:
        pass
    return {
        "current_version": __version__,
        "latest_version": __version__,
        "update_available": False,
        "release_notes": "All systems up to date.",
        "hotpatch_url": ""
    }


def apply_hotpatch_update(hotpatch_url: str) -> Dict[str, Any]:
    """Download and unpack hotpatch archive into local runtime directory."""
    if not hotpatch_url:
        return {"success": False, "message": "No hotpatch archive specified"}
    try:
        import tarfile, zipfile, tempfile
        req = urllib.request.Request(hotpatch_url, headers={"User-Agent": "Vigyan-Pro-Desktop"})
        target_dir = os.path.expanduser("~/.vigyan/desktop/")
        os.makedirs(target_dir, exist_ok=True)
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            with urllib.request.urlopen(req, timeout=15.0) as resp:
                tmp.write(resp.read())
            tmp_path = tmp.name

        if hotpatch_url.endswith(".zip"):
            with zipfile.ZipFile(tmp_path, "r") as zf:
                zf.extractall(target_dir)
        elif hotpatch_url.endswith((".tar.gz", ".tgz")):
            with tarfile.open(tmp_path, "r:gz") as tf:
                tf.extractall(target_dir)
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        return {"success": True, "message": "Hotpatch applied. Reloading UI...", "target_dir": target_dir}
    except Exception as e:
        return {"success": False, "message": f"Update failed: {str(e)}"}


# ==============================================================================
# 3.3 EMBEDDED LOCAL SOVEREIGN AGENT & NEURO-SYMBOLIC BRIDGE (PORT 8085)
# ==============================================================================
class _NeuroSymbolicHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Keep console clean

    def _send_cors(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_OPTIONS(self):
        self._send_cors(200)

    def do_GET(self):
        if self.path.startswith("/health") or self.path.startswith("/api/telemetry"):
            tel = get_system_telemetry()
            payload = dict(tel)
            payload.update({
                "status": "online",
                "agent": "Vigyan-Sovereign-Neuro-Symbolic-Bridge",
                "sympy": _SYMPY_ENGINE is not None,
                "kuzudb": True,
                "ram_governor": {"active": True, "threshold_pct": 88.0},
                "telemetry": tel,
            })
            self._send_cors(200)
            self.wfile.write(json.dumps(payload).encode("utf-8"))
        elif self.path.startswith("/api/models/catalog"):
            tel = get_system_telemetry()
            ram_gb = tel.get("ram_total_gb", 8.0)
            rec_tag = "vigyan:1.5b"
            payload = {
                "catalog": MODELS_CATALOG,
                "recommended_tag": rec_tag,
                "system_ram_gb": ram_gb,
                "downloads": _DOWNLOAD_MGR.get_status()
            }
            self._send_cors(200)
            self.wfile.write(json.dumps(payload).encode("utf-8"))
        elif self.path.startswith("/api/models/download/status"):
            query_tag = None
            if "?" in self.path:
                from urllib.parse import parse_qs, urlparse
                qs = parse_qs(urlparse(self.path).query)
                query_tag = qs.get("tag", [None])[0]
            st = _DOWNLOAD_MGR.get_status(query_tag)
            self._send_cors(200)
            self.wfile.write(json.dumps(st).encode("utf-8"))
        elif self.path.startswith("/api/workspace/list"):
            from urllib.parse import parse_qs, urlparse
            qs = parse_qs(urlparse(self.path).query)
            p = qs.get("path", ["."])[0]
            res = list_workspace_dir(p)
            self._send_cors(200)
            self.wfile.write(json.dumps(res).encode("utf-8"))
        elif self.path.startswith("/api/system/update/check"):
            res = check_github_update()
            self._send_cors(200)
            self.wfile.write(json.dumps(res).encode("utf-8"))
        else:
            # Universal cross-platform static file serving (served from local src directory)
            clean_path = self.path.split("?")[0]
            if clean_path in ("/", "/index.html", "/chat"):
                target_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
                if os.path.isfile(target_file):
                    self._send_cors(200, content_type="text/html; charset=utf-8")
                    with open(target_file, "rb") as f:
                        self.wfile.write(f.read())
                    return
            elif clean_path.startswith(("/vendor/", "/assets/")):
                rel = clean_path.lstrip("/")
                target_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), rel)
                if os.path.isfile(target_file):
                    ctype = "application/octet-stream"
                    if clean_path.endswith(".js"):
                        ctype = "application/javascript"
                    elif clean_path.endswith(".css"):
                        ctype = "text/css"
                    elif clean_path.endswith(".woff2"):
                        ctype = "font/woff2"
                    elif clean_path.endswith(".png"):
                        ctype = "image/png"
                    elif clean_path.endswith((".jpg", ".jpeg")):
                        ctype = "image/jpeg"
                    elif clean_path.endswith(".svg"):
                        ctype = "image/svg+xml"
                    self._send_cors(200, content_type=ctype)
                    with open(target_file, "rb") as f:
                        self.wfile.write(f.read())
                    return
            self._send_cors(404)
            self.wfile.write(b'{"error":"not found"}')

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            body = json.loads(raw)
        except Exception:
            body = {}

        if self.path.startswith("/api/system/update/apply"):
            url = body.get("hotpatch_url", "")
            res = apply_hotpatch_update(url)
            self._send_cors(200)
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        if self.path.startswith("/api/enrich"):
            q = body.get("query") or body.get("message") or ""
            res = enrich_stem_query(q)
            self._send_cors(200)
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        if self.path.startswith("/api/compute_mode"):
            mode = body.get("mode", "auto")
            stats = get_system_telemetry(override_mode=mode)
            self._send_cors(200)
            self.wfile.write(json.dumps(stats).encode("utf-8"))
            return

        if self.path.startswith("/api/models/download"):
            if self.path.endswith("/cancel"):
                tag = body.get("tag", "")
                cancelled = _DOWNLOAD_MGR.cancel_download(tag)
                self._send_cors(200)
                self.wfile.write(json.dumps({"success": cancelled, "tag": tag}).encode("utf-8"))
                return
            tag = body.get("model_id") or body.get("tag") or "vigyan:1.5b"
            res = _DOWNLOAD_MGR.start_download(tag)
            self._send_cors(200)
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        if self.path.startswith("/api/models/evict"):
            tag = body.get("model") or body.get("tag") or ""
            targets = [tag] if tag else ["vigyan:1.5b"]
            evicted = []
            for m in targets:
                try:
                    ev_req = urllib.request.Request(
                        "http://127.0.0.1:11434/api/generate",
                        data=json.dumps({"model": m, "prompt": "", "keep_alive": 0}).encode("utf-8"),
                        headers={"Content-Type": "application/json"}
                    )
                    with urllib.request.urlopen(ev_req, timeout=2.5) as ev_resp:
                        if ev_resp.status == 200:
                            evicted.append(m)
                except Exception:
                    pass
            stats = get_system_telemetry()
            self._send_cors(200)
            self.wfile.write(json.dumps({"success": True, "evicted": evicted, "telemetry": stats}).encode("utf-8"))
            return

        if self.path.startswith("/api/workspace/list"):
            p = body.get("path", ".")
            res = list_workspace_dir(p)
            self._send_cors(200)
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        if self.path.startswith("/api/workspace/read"):
            p = body.get("path", "")
            s = int(body.get("start_line", 1))
            e = int(body.get("end_line", 200))
            res = read_workspace_file(p, s, e)
            self._send_cors(200)
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        if self.path.startswith("/api/workspace/write"):
            p = body.get("path", "")
            c = body.get("content", "")
            ov = bool(body.get("overwrite", False))
            res = write_workspace_file(p, c, ov)
            self._send_cors(200)
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        if self.path.startswith("/api/workspace/grep"):
            q = body.get("query", "")
            p = body.get("path", ".")
            res = grep_workspace_files(q, p)
            self._send_cors(200)
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        if self.path.startswith("/api/agent/execute_cmd"):
            cmd = body.get("command", "")
            confirmed = bool(body.get("confirmed", False))
            cwd = body.get("cwd")
            res = execute_shell_command(cmd, confirmed=confirmed, cwd=cwd)
            self._send_cors(200)
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        if self.path.startswith("/api/chat") or self.path.startswith("/api/agent/stream"):
            user_query = (body.get("query") or body.get("message") or "").strip()
            requested_model = body.get("model") or "auto"
            
            enrichment = enrich_stem_query(user_query)

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            def _emit(event: str, data_obj: Any):
                chunk = f"event: {event}\ndata: {json.dumps(data_obj)}\n\n"
                try:
                    self.wfile.write(chunk.encode("utf-8"))
                    self.wfile.flush()
                except Exception:
                    pass

            # Grounding and axioms
            if enrichment.get("sympy"):
                s = enrichment["sympy"]
                _emit("sympy", f"$${s.get('latex', s.get('result'))}$$")
                _emit("think", f"SymPy AST Verified: {s.get('expression')} => {s.get('result')}\n")
                _emit("tool_result", {
                    "tool": "sympy_eval",
                    "success": True,
                    "expression": s.get("expression"),
                    "result": s.get("result"),
                    "latex": s.get("latex"),
                    "numeric_approx": s.get("numeric_approx")
                })
            if enrichment.get("graph_axioms"):
                cites = [f"[{a['domain']}: {a['law']}] {a['equation']}" for a in enrichment["graph_axioms"]]
                _emit("memory", "<br>• " + "<br>• ".join(cites))

            # Fast-path deterministic STEM visualizer card generation
            deterministic_executed = False
            q_lower = user_query.lower()
            
            # 1. Plotting Intent
            if any(w in q_lower for w in ("plot", "graph", "curve", "oscillat")):
                m_plot = re.search(r"(?:plot|graph)\s+(?:the\s+)?(?:damped\s+oscillation\s+)?(?:function\s+)?(?:f\(x\)\s*=\s*)?([^\n,;]+?)\s+from\s+([-\d\.]+)\s+to\s+([-\d\.]+)", q_lower)
                if m_plot:
                    expr_str, x_min_str, x_max_str = m_plot.groups()
                    expr_clean = expr_str.replace("with high resolution", "").replace("with resolution", "").replace("with high", "").strip()
                    expr_clean = re.sub(r"\s+(?:with|in|for|at|using)\b.*$", "", expr_clean)
                    try:
                        x_min = float(x_min_str)
                        x_max = float(x_max_str)
                        plot_res = evaluate_plot(expression=expr_clean, x_min=x_min, x_max=x_max, points=300, title=f"f(x) = {expr_clean}")
                        if plot_res.get("success"):
                            _emit("tool_result", plot_res)
                            deterministic_executed = True
                    except Exception:
                        pass
                elif "damped" in q_lower or ("exp" in q_lower and "cos" in q_lower):
                    plot_res = evaluate_plot(expression="exp(-0.15*x)*cos(2*x)", x_min=0.0, x_max=25.0, points=300, title="Damped Oscillation f(x) = exp(-0.15x)cos(2x)")
                    if plot_res.get("success"):
                        _emit("tool_result", plot_res)
                        deterministic_executed = True
                elif "sin" in q_lower and "exp" in q_lower:
                    plot_res = evaluate_plot(expression="sin(x)*exp(-0.2*x)", x_min=0.0, x_max=20.0, points=300, title="Damped Sine Wave f(x) = sin(x)*exp(-0.2x)")
                    if plot_res.get("success"):
                        _emit("tool_result", plot_res)
                        deterministic_executed = True

            # 2. Circuit Intent
            if not deterministic_executed and any(w in q_lower for w in ("circuit", "filter", "cutoff", "rc lowpass", "rlc", "555")):
                if "rc" in q_lower or "filter" in q_lower:
                    circ_res = calc_circuit("rc_filter", {"r": 10000.0, "c": 1e-7, "filter_type": "lowpass"})
                    _emit("tool_result", circ_res)
                    deterministic_executed = True
                elif "rlc" in q_lower or "reson" in q_lower:
                    circ_res = calc_circuit("rlc_resonance", {"r": 10.0, "l": 0.01, "c": 1e-6, "config": "series"})
                    _emit("tool_result", circ_res)
                    deterministic_executed = True
                elif "555" in q_lower or "timer" in q_lower:
                    circ_res = calc_circuit("555_timer", {"r1": 10000.0, "r2": 47000.0, "c": 1e-6})
                    _emit("tool_result", circ_res)
                    deterministic_executed = True

            # 3. Physics / Orbit Intent
            if not deterministic_executed and any(w in q_lower for w in ("orbit", "kepler", "satellite", "projectile", "ballistic")):
                if "orbit" in q_lower or "kepler" in q_lower or "satellite" in q_lower:
                    phys_res = calc_physics("kepler_orbit", {"a": 7000.0, "e": 0.05, "body": "earth"})
                    _emit("tool_result", phys_res)
                    deterministic_executed = True
                elif "projectile" in q_lower or "ballistic" in q_lower:
                    phys_res = calc_physics("projectile", {"velocity": 50.0, "angle_deg": 45.0, "height": 0.0})
                    _emit("tool_result", phys_res)
                    deterministic_executed = True

            # 4. Material Science Intent
            if not deterministic_executed and any(w in q_lower for w in ("/material", "crystallography", "unit cell", "bragg", "fcc", "bcc", "hcp", "perovskite", "eutectic", "lever rule")):
                mat_type = "crystal_lattice"
                lat_type = "FCC"
                if "phase" in q_lower or "eutectic" in q_lower or "lever" in q_lower:
                    mat_type = "phase_diagram"
                elif "xrd" in q_lower or "bragg" in q_lower or "diffraction" in q_lower:
                    mat_type = "xrd"
                elif "bcc" in q_lower:
                    lat_type = "BCC"
                elif "hcp" in q_lower:
                    lat_type = "HCP"
                elif "diamond" in q_lower:
                    lat_type = "Diamond"
                elif "perovskite" in q_lower:
                    lat_type = "Perovskite"
                
                mat_res = {
                    "tool": "material_science",
                    "render_type": "material_science",
                    "success": True,
                    "title": f"Crystallographic Analysis ({lat_type if mat_type == 'crystal_lattice' else mat_type.title()})",
                    "type": mat_type,
                    "latticeType": lat_type,
                    "materialName": f"{lat_type} Crystal Matrix",
                    "parameters": {"temperature": 220, "composition": 40}
                }
                _emit("tool_result", mat_res)
                deterministic_executed = True

            # 5. Molecular Biology Intent
            if not deterministic_executed and any(w in q_lower for w in ("/biology", "dna", "double helix", "bilayer", "membrane", "glycolysis", "krebs", "tca")):
                bio_type = "dna_helix"
                if "membrane" in q_lower or "lipid" in q_lower or "channel" in q_lower:
                    bio_type = "cell_membrane"
                elif "protein" in q_lower or "folding" in q_lower or "sheet" in q_lower:
                    bio_type = "protein_folding"
                elif "respiration" in q_lower or "glycolysis" in q_lower or "krebs" in q_lower or "tca" in q_lower:
                    bio_type = "metabolic_pathway"
                
                bio_res = {
                    "tool": "biology_viewer",
                    "render_type": "biology_viewer",
                    "success": True,
                    "title": f"Biological System: {bio_type.replace('_', ' ').title()}",
                    "type": bio_type,
                    "parameters": {"channelOpen": True, "atpYield": 32}
                }
                _emit("tool_result", bio_res)
                deterministic_executed = True

            # 6. Advanced 3D Math Intent
            if not deterministic_executed and any(w in q_lower for w in ("/math3d", "saddle", "hyperbolic paraboloid", "vector field", "curl", "divergence", "taylor series")):
                m_type = "saddle"
                if "vector" in q_lower or "curl" in q_lower or "div" in q_lower:
                    m_type = "vector_field"
                elif "taylor" in q_lower or "series" in q_lower:
                    m_type = "taylor_series"
                
                math_res = {
                    "tool": "math_visualizer",
                    "render_type": "math_visualizer",
                    "success": True,
                    "title": f"Higher Mathematics: {m_type.replace('_', ' ').title()}",
                    "type": m_type,
                    "parameters": {"a": 2.0, "b": 2.0, "degree": 5}
                }
                _emit("tool_result", math_res)
                deterministic_executed = True

            # 7. Clinical Decision Support Intent
            if not deterministic_executed and any(w in q_lower for w in ("/medical", "stemi", "ecg", "septic shock", "pulmonary embolism", "differential diagnosis")):
                med_condition = "stemi"
                if "shock" in q_lower or "sepsis" in q_lower:
                    med_condition = "septic_shock"
                elif "embolism" in q_lower or "pe" in q_lower:
                    med_condition = "pulmonary_embolism"
                
                med_res = {
                    "tool": "medical_viewer",
                    "render_type": "medical_viewer",
                    "success": True,
                    "title": f"Clinical Protocol: {med_condition.replace('_', ' ').upper()}",
                    "condition": med_condition
                }
                _emit("tool_result", med_res)
                deterministic_executed = True

            sys_prompt = (
                "You are Vigyan AI 1.5B Quad Master, a sovereign STEM, math, and physics intelligence system architected by Shreyansh Singh. "
                "Solve problems with mathematical precision, concise explanations, and clean LaTeX ($$...$$). Be direct, rigorous, and professional."
            )
            if enrichment.get("sympy"):
                s = enrichment["sympy"]
                sys_prompt += f"\n[SymPy Verified Grounding]: {s.get('expression')} = {s.get('result')}"

            # Sovereign Offline Ollama with RAM Governor
            cascade = select_cascade_model(requested_model, user_query)
            active_model = cascade["model"]
            _emit("cascade_tier", cascade)
            if cascade.get("downgraded"):
                _emit("tier_downgrade", cascade)
                _emit("think", f"[RAM Guard]: System routed to {active_model} Sovereign Engine.\n")

            try:
                hybrid = enrichment["hybrid"]
                raw_messages = body.get("messages") or []
                if raw_messages:
                    full_msgs = [{"role": "system", "content": sys_prompt}] + raw_messages
                    model_messages = compress_conversation_history(full_msgs, max_tokens_est=650)
                else:
                    model_messages = [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_query},
                    ]
                user_temp = body.get("temperature")
                if user_temp is None:
                    user_temp = body.get("options", {}).get("temperature", 0.05)
                try:
                    user_temp = max(0.0, min(2.0, float(user_temp)))
                except Exception:
                    user_temp = 0.05

                user_ctx = None
                try:
                    if body.get("num_ctx"):
                        user_ctx = int(body.get("num_ctx"))
                    elif body.get("options", {}).get("num_ctx"):
                        user_ctx = int(body.get("options", {}).get("num_ctx"))
                except Exception:
                    user_ctx = None

                ollama_payload = {
                    "model": active_model,
                    "messages": model_messages,
                    "options": {
                        "num_gpu": hybrid["num_gpu"],
                        "num_thread": hybrid["num_thread"],
                        "num_ctx": user_ctx or 1024,
                        "num_batch": 64,
                        "num_predict": 1024,
                        "temperature": user_temp,
                        "stop": ["<|im_start|>", "<|im_end|>", "<|endoftext|>", "User:", "\n\nUser", "Human:"]
                    },
                    "stream": True,
                }

                gov_thresh = 96.0
                try:
                    if body.get("governor_threshold_pct"):
                        gov_thresh = float(body.get("governor_threshold_pct"))
                    elif body.get("options", {}).get("governor_threshold_pct"):
                        gov_thresh = float(body.get("options", {}).get("governor_threshold_pct"))
                except Exception:
                    gov_thresh = 96.0

                if active_model == "vigyan:1.5b":
                    gov_thresh = max(94.0, min(97.5, gov_thresh))
                else:
                    gov_thresh = max(60.0, min(95.0, gov_thresh))

                governor_tripped = [False]
                def _on_ram_trip(pct):
                    governor_tripped[0] = True
                    _emit("ram_governor_trip", {
                        "ram_percent": pct,
                        "threshold": gov_thresh,
                        "evicted_model": active_model,
                        "fallback": "vigyan:1.5b"
                    })
                    _emit("token", f"\n\n⚠️ **[RAM Governor Safety Alert]**: Memory reached {pct:.1f}% (≥ {gov_thresh:.0f}% threshold). Model `{active_model}` was unloaded to prevent system lockup.")

                governor = RAMGovernor(threshold_pct=gov_thresh, interval_sec=0.1)
                governor.start(_on_ram_trip, active_model)

                req = urllib.request.Request(
                    "http://127.0.0.1:11434/api/chat",
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(ollama_payload).encode("utf-8"),
                )

                # Keep-alive silent heartbeat thread to prevent socket drop without user-facing noise
                _emit("status", {"type": "thinking"})
                hb_stop = threading.Event()
                def _heartbeat_worker():
                    step = 0
                    while not hb_stop.is_set():
                        time.sleep(1.5)
                        if hb_stop.is_set():
                            break
                        step += 1
                        _emit("heartbeat", {"type": "ping", "step": step})

                hb_t = threading.Thread(target=_heartbeat_worker, daemon=True)
                hb_t.start()

                accumulated_text = ""
                try:
                    with urllib.request.urlopen(req, timeout=180) as resp:
                        hb_stop.set()
                        _emit("status", {"type": "ready", "message": "Inference stream active"})
                        for line in resp:
                            if governor_tripped[0]:
                                break
                            line_s = line.decode("utf-8").strip()
                            if not line_s:
                                continue
                            chunk = json.loads(line_s)
                            tok = chunk.get("message", {}).get("content", "")
                            if tok:
                                accumulated_text += tok
                                _emit("token", tok)
                finally:
                    hb_stop.set()

                governor.stop()
                self._parse_and_execute_tools(accumulated_text, _emit)

            except Exception as exc:
                if enrichment.get("sympy"):
                    s = enrichment["sympy"]
                    fallback = (
                        f"### Exact Closed-Form Symbolic Solution\n\n"
                        f"**Evaluated AST:** `{s.get('expression')}`\n\n"
                        f"$$\\mathbf{{{s.get('latex')}}}$$\n\n"
                        f"**Numerical Approximation:** `{s.get('numeric_approx')}`\n"
                    )
                    _emit("token", fallback)
                elif enrichment.get("graph_axioms"):
                    ax = enrichment["graph_axioms"][0]
                    fallback = (
                        f"### {ax['law']} ({ax['domain']})\n\n"
                        f"$$\\mathbf{{{ax['equation']}}}$$\n\n"
                        f"{ax['axiom']}\n"
                    )
                    _emit("token", fallback)
                else:
                    _emit("token", f"[Neuro-Symbolic Notice: {exc}]")

            _emit("done", {})
            return

        self._send_cors(404)
        self.wfile.write(b'{"error":"unknown endpoint"}')

    def _parse_and_execute_tools(self, text: str, emit_fn):
        tool_matches = re.findall(r"<tool_call>(.*?)</tool_call>", text, re.DOTALL)
        for t_str in tool_matches:
            try:
                t_data = json.loads(t_str.strip())
                t_name = t_data.get("name")
                t_args = t_data.get("arguments", {})
                if t_name == "execute_cmd":
                    cmd = t_args.get("command", "")
                    exec_res = execute_shell_command(cmd, confirmed=False)
                    if exec_res.get("status") == "requires_approval":
                        emit_fn("requires_approval", exec_res)
                    else:
                        emit_fn("tool_result", exec_res)
                elif t_name == "list_dir":
                    emit_fn("tool_result", {"tool": "list_dir", "result": list_workspace_dir(t_args.get("path", "."))})
                elif t_name == "read_file":
                    emit_fn("tool_result", {"tool": "read_file", "result": read_workspace_file(t_args.get("path", ""), t_args.get("start_line", 1), t_args.get("end_line", 200))})
                elif t_name == "write_file":
                    p = t_args.get("path", "")
                    c = t_args.get("content", "")
                    w_res = write_workspace_file(p, c, overwrite=False)
                    if w_res.get("status") == "requires_approval":
                        emit_fn("requires_approval", w_res)
                    else:
                        emit_fn("tool_result", {"tool": "write_file", "result": w_res})
                elif t_name == "grep_files":
                    emit_fn("tool_result", {"tool": "grep_files", "result": grep_workspace_files(t_args.get("query", ""), t_args.get("path", "."))})
                elif t_name == "sympy_eval":
                    expr = t_args.get("expression", "")
                    if _SYMPY_ENGINE:
                        eval_res = _SYMPY_ENGINE.evaluate_expression(expr)
                        emit_fn("sympy", f"$${eval_res.get('latex', eval_res.get('result'))}$$")
                        emit_fn("tool_result", {
                            "tool": "sympy_eval",
                            "success": True,
                            "expression": expr,
                            "result": eval_res.get("result", ""),
                            "latex": eval_res.get("latex", ""),
                            "numeric": eval_res.get("numeric_approx", "")
                        })
                elif t_name == "plot_function":
                    expr = t_args.get("expression", "x**2")
                    x_min = t_args.get("x_min", -10.0)
                    x_max = t_args.get("x_max", 10.0)
                    pts = t_args.get("points", 200)
                    title = t_args.get("title", "")
                    x_lbl = t_args.get("x_label", "x")
                    y_lbl = t_args.get("y_label", "y")
                    plot_res = evaluate_plot(expr, x_min, x_max, pts, title, x_lbl, y_lbl)
                    emit_fn("tool_result", plot_res)
                elif t_name == "circuit_calc":
                    ctype = t_args.get("circuit_type", "rc_filter")
                    cparams = t_args.get("params") if isinstance(t_args.get("params"), dict) else t_args
                    circ_res = calc_circuit(ctype, cparams)
                    emit_fn("tool_result", circ_res)
                elif t_name == "physics_sim":
                    stype = t_args.get("sim_type", "kepler_orbit")
                    sparams = t_args.get("params") if isinstance(t_args.get("params"), dict) else t_args
                    phys_res = calc_physics(stype, sparams)
                    emit_fn("tool_result", phys_res)
                elif tools and t_name in tools.get_all_tools():
                    tool_res = tools.dispatch_tool(t_name, t_args)
                    emit_fn("tool_result", tool_res)
            except Exception:
                pass


def start_neuro_symbolic_bridge_server(port: int = 8085) -> Optional[int]:
    """Start embedded Neuro-Symbolic HTTP server on port 8085 (or 8086 if 8085 is in use)."""
    for candidate_port in (port, 8086):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", candidate_port), _NeuroSymbolicHTTPHandler)
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            return candidate_port
        except OSError:
            continue
    return None


# ==============================================================================
# 4. OLLAMA DAEMON SUPERVISOR & WEBKITGTK WORKSTATION SHELL
# ==============================================================================
def _ollama_is_healthy() -> bool:
    """Return True if a local Ollama answers on its loopback port."""
    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False


OLLAMA = OllamaSupervisor(["ollama", "serve"], is_healthy=_ollama_is_healthy)


def ensure_ollama_daemon() -> None:
    """Make sure a local Ollama is running; start one we own if it is not."""
    try:
        OLLAMA.start()
    except OSError as exc:  # e.g. ollama is not installed
        print(f"[WARN] could not start ollama: {exc}", file=sys.stderr)


def _watch_ollama() -> bool:
    """GLib timer callback: restart a crashed Ollama child. True keeps the timer."""
    OLLAMA.check()
    return True


def main():
    # Lower process priority to nice 10 to yield CPU cycles to foreground user apps
    try:
        os.nice(10)
    except Exception:
        pass

    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('WebKit2', '4.1')
    from gi.repository import Gtk, WebKit2, Gdk, GdkPixbuf, GLib

    # Exit through the GTK main loop so the cleanup after Gtk.main() always runs.
    try:
        from gi.repository import GLibUnix
        GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, Gtk.main_quit)
        GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, Gtk.main_quit)
    except Exception:
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, Gtk.main_quit)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, Gtk.main_quit)

    # Wayland / XDG application identity mapping
    GLib.set_prgname("vigyan-pro")
    GLib.set_application_name("Vigyan Pro")

    # Initialize hardware topology cache, Ollama daemon, and Neuro-Symbolic bridge
    _discover_static_hardware()
    ensure_ollama_daemon()
    bridge_port = start_neuro_symbolic_bridge_server(8085) or 8085

    win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    win.set_title("Vigyan Pro")
    win.set_role("vigyan-pro")
    win.set_default_size(1340, 740)
    win.set_position(Gtk.WindowPosition.CENTER)

    # Modern CSS Provider for pitch-black background
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(b"window { background-color: #000000; }")
    win.get_style_context().add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    # Icon resolution
    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_candidates = [
        os.path.join(base_dir, "..", "assets", "micro_logo_v.png"),
        os.path.join(base_dir, "assets", "micro_logo_v.png"),
        "/opt/vigyan-pro/assets/micro_logo_v.png",
        "/usr/share/icons/hicolor/256x256/apps/vigyan-pro.png",
        os.path.expanduser("~/.local/share/icons/hicolor/256x256/apps/vigyan-pro.png"),
        os.path.expanduser("~/.vigyan/build/favicon.png")
    ]
    icon_path = next((p for p in icon_candidates if os.path.exists(p)), None)
    if icon_path:
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon_path)
            win.set_icon(pixbuf)
            Gtk.Window.set_default_icon(pixbuf)
            win.set_icon_name("vigyan-pro")
        except Exception:
            pass

    # WebKit Settings & UserContentManager IPC
    settings = WebKit2.Settings()
    settings.set_enable_javascript(True)
    settings.set_enable_webgl(True)
    settings.set_enable_write_console_messages_to_stdout(True)
    settings.set_allow_file_access_from_file_urls(True)
    settings.set_allow_universal_access_from_file_urls(True)
    settings.set_enable_smooth_scrolling(True)
    try:
        settings.set_hardware_acceleration_policy(WebKit2.HardwareAccelerationPolicy.ALWAYS)
    except Exception:
        pass

    ucm = WebKit2.UserContentManager()

    def _eval_js(js_code: str):
        if hasattr(webview, "evaluate_javascript"):
            webview.evaluate_javascript(js_code, -1, None, None, None, None, None)
        else:
            webview.run_javascript(js_code, None, None, None)

    # Native IPC Message Handler (Bidirectional Communication: Telemetry, Hybrid Mode, Neuro-Symbolic AST/GraphRAG)
    def on_script_message(manager, js_result):
        try:
            val = js_result.get_js_value() if hasattr(js_result, "get_js_value") else js_result.to_value()
            if val and val.is_string():
                data = json.loads(val.to_string())
                action = data.get("action") or data.get("cmd")
                if action == "get_telemetry":
                    stats = get_system_telemetry()
                    _eval_js(f"window.onNativeTelemetry && window.onNativeTelemetry({json.dumps(stats)});")
                elif action == "set_compute_mode":
                    mode = data.get("mode", "auto")
                    stats = get_system_telemetry(override_mode=mode)
                    _eval_js(f"window.onNativeTelemetry && window.onNativeTelemetry({json.dumps(stats)});")
                elif action in ("neuro_symbolic_query", "enrich"):
                    req_id = data.get("reqId", "")
                    query_str = data.get("query", "")
                    enriched = enrich_stem_query(query_str)
                    enriched["reqId"] = req_id
                    _eval_js(f"window.__onNeuroSymbolicResult && window.__onNeuroSymbolicResult({json.dumps(enriched)});")
        except Exception as e:
            print(f"[IPC ERR] {e}", file=sys.stderr)

    ucm.register_script_message_handler("nativeHost")
    ucm.connect("script-message-received::nativeHost", on_script_message)

    # WebKit View
    webview = WebKit2.WebView.new_with_user_content_manager(ucm)
    webview.set_settings(settings)
    webview.set_background_color(Gdk.RGBA(0, 0, 0, 1))

    # Periodic Hardware Telemetry Broadcast (every 3 seconds, <0.2ms sysfs read)
    def _push_telemetry():
        try:
            stats = get_system_telemetry()
            _eval_js(f"window.onNativeTelemetry && window.onNativeTelemetry({json.dumps(stats)});")
        except Exception:
            pass
        return True

    GLib.timeout_add_seconds(3, _push_telemetry)

    # Enterprise Navigation Policy: Prevent webview URL hijacking / unauthorized redirection
    def on_decide_policy(view, decision, decision_type):
        if decision_type == WebKit2.PolicyDecisionType.NAVIGATION_ACTION:
            action = decision.get_navigation_action()
            req = action.get_request()
            uri = req.get_uri() if req else ""
            if uri.startswith("file://") or uri.startswith("about:blank"):
                return False
            decision.ignore()
            try:
                import webbrowser
                webbrowser.open(uri)
            except Exception:
                pass
            return True
        return False

    webview.connect("decide-policy", on_decide_policy)

    # Dynamic index.html discovery
    index_candidates = [
        os.path.join(base_dir, "index.html"),
        "/opt/vigyan-pro/src/index.html",
        os.path.expanduser("~/.vigyan/desktop/index.html")
    ]
    index_path = next((p for p in index_candidates if os.path.exists(p)), index_candidates[0])
    webview.load_uri(f"file://{os.path.abspath(index_path)}")

    # Push initial telemetry and sync bridge port as soon as page finishes loading
    def on_load_finished(view, event):
        if event == WebKit2.LoadEvent.FINISHED:
            _eval_js(f"window.AGENT_HOST = 'http://127.0.0.1:{bridge_port}'; try {{ localStorage.setItem('vigyan_agent_host', 'http://127.0.0.1:{bridge_port}'); }} catch(e){{}}")
            GLib.timeout_add(300, lambda: (_push_telemetry() and False))

    webview.connect("load-changed", on_load_finished)

    # Keyboard shortcuts: F11 Fullscreen, Ctrl+R Reload, Ctrl + / - / 0 Zoom
    def on_key_press(widget, event):
        keyval = event.keyval
        state = event.state
        if keyval == Gdk.KEY_F11:
            if win.get_window().get_state() & Gdk.WindowState.FULLSCREEN:
                win.unfullscreen()
            else:
                win.fullscreen()
            return True
        elif state & Gdk.ModifierType.CONTROL_MASK:
            if keyval in (Gdk.KEY_r, Gdk.KEY_R):
                webview.reload()
                return True
            elif keyval in (Gdk.KEY_plus, Gdk.KEY_equal, Gdk.KEY_KP_Add):
                _eval_js("window.applyUiZoom && window.applyUiZoom((window.uiZoomLevel || 1.0) + 0.1);")
                return True
            elif keyval in (Gdk.KEY_minus, Gdk.KEY_underscore, Gdk.KEY_KP_Subtract):
                _eval_js("window.applyUiZoom && window.applyUiZoom((window.uiZoomLevel || 1.0) - 0.1);")
                return True
            elif keyval in (Gdk.KEY_0, Gdk.KEY_KP_0):
                _eval_js("window.applyUiZoom && window.applyUiZoom(1.0);")
                return True
        return False

    win.connect("key-press-event", on_key_press)
    win.add(webview)
    win.connect("destroy", Gtk.main_quit)

    snapshot_path = None
    if "--snapshot" in sys.argv:
        idx = sys.argv.index("--snapshot")
        if idx + 1 < len(sys.argv):
            snapshot_path = sys.argv[idx + 1]

    if snapshot_path:
        def on_snapshot_done(view, res, target):
            try:
                surface = view.get_snapshot_finish(res)
                surface.write_to_png(target)
                print(f"[OK] Snapshot saved to {target}")
            except Exception as e:
                print(f"[ERR] Snapshot failed: {e}")
            Gtk.main_quit()

        def trigger_snapshot():
            webview.get_snapshot(
                WebKit2.SnapshotRegion.FULL_DOCUMENT,
                WebKit2.SnapshotOptions.NONE,
                None,
                on_snapshot_done,
                snapshot_path
            )
            return False

        def on_load_changed(view, event):
            if event == WebKit2.LoadEvent.FINISHED:
                GLib.timeout_add(1500, trigger_snapshot)

        webview.connect("load-changed", on_load_changed)

    win.show_all()
    win.present()
    GLib.timeout_add_seconds(5, _watch_ollama)

    # Low-priority background pre-warming for zero-latency first prompt
    def _prewarm_moe():
        time.sleep(2.0)  # Wait for UI window to finish layout
        ensure_vigyan_1_5b_registered()
        try:
            pw_req = urllib.request.Request(
                "http://127.0.0.1:11434/api/generate",
                data=json.dumps({
                    "model": "vigyan:1.5b",
                    "prompt": "",
                    "keep_alive": "60m",
                    "options": {"num_ctx": 2048, "num_batch": 128}
                }).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(pw_req, timeout=35.0) as pw_resp:
                if pw_resp.status == 200:
                    print("[INFO] Pre-warmed vigyan:1.5b Quad Master into memory.", file=sys.stderr)
        except Exception:
            pass

    threading.Thread(target=_prewarm_moe, daemon=True).start()

    try:
        Gtk.main()
    finally:
        OLLAMA.stop()


if __name__ == "__main__":
    main()
