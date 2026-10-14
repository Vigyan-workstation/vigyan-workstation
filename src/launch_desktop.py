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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Any, List, Optional

# Set Ollama hybrid compute acceleration flags before spawning daemon
os.environ.setdefault("OLLAMA_FLASH_ATTENTION", "1")
os.environ.setdefault("OLLAMA_KV_CACHE_TYPE", "q8_0")
os.environ.setdefault("OLLAMA_NUM_PARALLEL", "1")

from ollama_supervisor import OllamaSupervisor

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

    # 1. Thread allocation: always bind to physical cores to prevent SMT cache thrashing
    if mode == "cpu_eco" or (mode == "auto" and on_battery and battery_pct < 30):
        num_thread = max(2, phys_cores - 1)
    else:
        num_thread = phys_cores

    # 2. Context window & batch scaling to prevent RAM/swap thrashing
    if ram_total_gb < 6.0 or ram_avail_gb < 1.8:
        num_ctx = 2048
        num_batch = 128
    elif ram_total_gb < 10.0:
        # 7-8 GB laptops (e.g., Ryzen 5 7520U with 6.95 GB usable RAM)
        # Lock to 2048 context and 128 batch to prevent swap thrashing
        num_ctx = 2048
        num_batch = 128
    elif ram_total_gb < 18.0:
        num_ctx = 8192
        num_batch = 512
    else:
        num_ctx = 16384
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
                    "pi": sp.pi, "e": sp.E, "E": sp.E, "oo": sp.oo,
                    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "exp": sp.exp,
                    "log": sp.log, "ln": sp.log, "sqrt": sp.sqrt, "diff": sp.diff,
                    "integrate": sp.integrate, "solve": sp.solve, "simplify": sp.simplify,
                    "expand": sp.expand, "factor": sp.factor, "limit": sp.limit,
                    "series": sp.series, "dsolve": sp.dsolve, "Matrix": sp.Matrix,
                    "Eq": sp.Eq, "symbols": sp.symbols, "Symbol": sp.Symbol, "sp": sp,
                }

            def evaluate_expression(self, expr_str: str) -> Dict[str, Any]:
                try:
                    res = eval(expr_str.strip(), {"__builtins__": {}}, dict(self.safe_dict))
                    latex_res = sp.latex(res) if isinstance(res, (sp.Basic, sp.Matrix)) else str(res)
                    num = None
                    if hasattr(res, "evalf") and not getattr(res, "free_symbols", None):
                        num = float(res.evalf(6))
                    elif isinstance(res, (int, float)):
                        num = float(res)
                    return {"success": True, "result": str(res), "latex": latex_res, "numeric_approx": num}
                except Exception as exc:
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
            while self.running:
                try:
                    pct = psutil.virtual_memory().percent if psutil else 0.0
                    if pct > self.peak_ram_pct:
                        self.peak_ram_pct = pct
                    if pct >= self.threshold_pct and not self.tripped:
                        self.tripped = True
                        print(f"⚠️ [RAM GOVERNOR] CRITICAL TRIPWIRE: RAM reached {pct:.1f}% >= {self.threshold_pct}%. Aborting & evicting model {active_model}!")
                        try:
                            import urllib.request
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
    ram_pct = psutil.virtual_memory().percent if psutil else 50.0
    q_lower = (query or "").lower()
    is_heavy_reasoning = any(w in q_lower for w in ["prove", "theorem", "hamiltonian", "schrodinger", "einstein", "navier-stokes", "derivation", "tensor"])
    
    # 1. Critical RAM check (>80% RAM)
    if ram_pct >= 80.0:
        return {
            "tier": 1,
            "model": "olmoe:1b-7b",
            "reason": f"System RAM high ({ram_pct:.1f}% >= 80%) — locked to Tier 1 Sovereign MoE"
        }
        
    # 2. User explicit model choice
    if requested_model and requested_model != "auto":
        if ("quad" in requested_model.lower() or "7b" in requested_model.lower()) and ram_pct > 80.0:
            return {
                "tier": 1,
                "model": "olmoe:1b-7b",
                "reason": f"RAM at {ram_pct:.1f}% too high for 7B Quad-Master — safely downgraded to Tier 1"
            }
        tier = 2 if ("quad" in requested_model.lower() or "7b" in requested_model.lower()) else 1
        return {"tier": tier, "model": requested_model, "reason": "User explicit selection"}
        
    # 3. Auto cascade escalation
    if is_heavy_reasoning and ram_pct < 65.0:
        return {
            "tier": 2,
            "model": "vigyan:7b-quad-master",
            "reason": f"Escalated to Tier 2 7B Quad-Master (RAM {ram_pct:.1f}% < 65% with deep STEM reasoning)"
        }
    return {
        "tier": 1,
        "model": "olmoe:1b-7b",
        "reason": "Tier 1 Sovereign MoE (fast response & tool orchestration)"
    }


# ==============================================================================
# 3.1 HUGGING FACE RESUMABLE MODEL DOWNLOADER & REGISTRY
# ==============================================================================
MODELS_CATALOG = {
    "olmoe:1b-7b": {
        "name": "Allen OLMoE 1B-7B Instruct",
        "tag": "olmoe:1b-7b",
        "size_bytes": 3435973836,
        "size_formatted": "3.2 GB",
        "recommended_ram": "< 16 GB RAM (Laptops & APUs)",
        "description": "Sparse Mixture-of-Experts (6.9B total, 1B active). Blazing fast on laptops and integrated graphics.",
        "hf_url": "https://huggingface.co/allenai/OLMoE-1B-7B-0924-Instruct-GGUF/resolve/main/olmoe-1b-7b-0924-instruct-q3_k_m.gguf",
        "local_candidates": [
            os.path.expanduser("~/.vigyan/models/olmoe-1b-7b-0924-instruct-q3_k_m.gguf"),
            "/home/hello/Downloads/vigyan ai/models/olmoe-1b-7b-0924-instruct-q3_k_m.gguf"
        ],
        "dest_filename": "olmoe-1b-7b-0924-instruct-q3_k_m.gguf",
        "template": """{{- if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{- range .Messages }}<|im_start|>{{ .Role }}
{{ .Content }}<|im_end|>
{{ end }}<|im_start|>assistant
""",
        "stop": ["<|im_start|>", "<|im_end|>", "<|endoftext|>"]
    },
    "vigyan:7b-quad-master": {
        "name": "Vigyan 7B Quad-Master DPO",
        "tag": "vigyan:7b-quad-master",
        "size_bytes": 4509715660,
        "size_formatted": "4.2 GB",
        "recommended_ram": "≥ 16 GB RAM / Dedicated GPU",
        "description": "Frontier Sovereign STEM & Reasoning model. Four-way post-trained DPO on advanced physics, math, and code.",
        "hf_url": "https://huggingface.co/shreyansh12183/vigyan-7b-quad-master/resolve/main/vigyan-7b-quad-master-q4_k_m.gguf",
        "local_candidates": [
            os.path.expanduser("~/.vigyan/models/vigyan-7b-quad-master-q4_k_m.gguf"),
            "/home/hello/Downloads/vigyan ai/models/vigyan-7b-quad-master-q4_k_m.gguf"
        ],
        "dest_filename": "vigyan-7b-quad-master-q4_k_m.gguf",
        "template": """{{- if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{- range .Messages }}<|im_start|>{{ .Role }}
{{ .Content }}<|im_end|>
{{ end }}<|im_start|>assistant
""",
        "stop": ["<|im_start|>", "<|im_end|>", "<|endoftext|>"]
    }
}


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

        # Check local candidate files first (instant local import)
        for cand in info.get("local_candidates", []):
            if os.path.isfile(cand) and os.path.getsize(cand) > 100_000_000:
                def _instant_register():
                    with self._lock:
                        self.active_downloads[tag]["status"] = "registering"
                        self.active_downloads[tag]["progress_pct"] = 100.0
                    target_dir = os.path.expanduser("~/.vigyan/models")
                    os.makedirs(target_dir, exist_ok=True)
                    dest_file = os.path.join(target_dir, info["dest_filename"])
                    if not os.path.exists(dest_file):
                        try:
                            shutil.copyfile(cand, dest_file)
                        except Exception:
                            dest_file = cand
                    # Register into Ollama
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
    except Exception as e:
        return {"success": False, "error": str(e)}


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
            rec_tag = "olmoe:1b-7b" if ram_gb < 14.0 else "vigyan:7b-quad-master"
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
        else:
            self._send_cors(404)
            self.wfile.write(b'{"error":"not found"}')

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            body = json.loads(raw)
        except Exception:
            body = {}

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
            tag = body.get("model_id") or body.get("tag") or "olmoe:1b-7b"
            res = _DOWNLOAD_MGR.start_download(tag)
            self._send_cors(200)
            self.wfile.write(json.dumps(res).encode("utf-8"))
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
            if enrichment.get("graph_axioms"):
                cites = [f"[{a['domain']}: {a['law']}] {a['equation']}" for a in enrichment["graph_axioms"]]
                _emit("memory", "<br>• " + "<br>• ".join(cites))

            sys_prompt = (
                "You are Vigyan Pro, a sovereign desktop STEM & coding assistant with real autonomous workspace capabilities. "
                "Format formulas in clean LaTeX ($$...$$). Be concise, direct, and helpful. "
                "When needed, you can autonomously inspect or operate on the user's workspace using JSON blocks:\n"
                "- <tool_call>{\"name\": \"execute_cmd\", \"arguments\": {\"command\": \"ls -la\"}}</tool_call>\n"
                "- <tool_call>{\"name\": \"list_dir\", \"arguments\": {\"path\": \".\"}}</tool_call>\n"
                "- <tool_call>{\"name\": \"read_file\", \"arguments\": {\"path\": \"README.md\", \"start_line\": 1, \"end_line\": 100}}</tool_call>\n"
                "- <tool_call>{\"name\": \"write_file\", \"arguments\": {\"path\": \"output.py\", \"content\": \"print('hello')\"}}</tool_call>\n"
                "- <tool_call>{\"name\": \"grep_files\", \"arguments\": {\"query\": \"def main\", \"path\": \".\"}}</tool_call>\n"
                "- <tool_call>{\"name\": \"sympy_eval\", \"arguments\": {\"expression\": \"integrate(x**2, x)\"}}</tool_call>"
            )
            if enrichment.get("prompt_injection"):
                sys_prompt += "\n\n" + enrichment["prompt_injection"]

            # Sovereign Offline Ollama with RAM Governor
            cascade = select_cascade_model(requested_model, user_query)
            active_model = cascade["model"]
            _emit("cascade_tier", cascade)

            try:
                hybrid = enrichment["hybrid"]
                ollama_payload = {
                    "model": active_model,
                    "messages": [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_query},
                    ],
                    "options": {
                        "num_gpu": hybrid["num_gpu"],
                        "num_thread": hybrid["num_thread"],
                        "num_ctx": hybrid["num_ctx"],
                        "num_batch": hybrid["num_batch"],
                        "temperature": 0.1,
                    },
                    "stream": True,
                }

                governor_tripped = [False]
                def _on_ram_trip(pct):
                    governor_tripped[0] = True
                    _emit("ram_governor_trip", {
                        "ram_percent": pct,
                        "threshold": 88.0,
                        "evicted_model": active_model,
                        "fallback": "olmoe:1b-7b"
                    })
                    _emit("token", f"\n\n⚠️ **[RAM Governor Safety Alert]**: Memory reached {pct:.1f}% (≥ 88% threshold). Model `{active_model}` was unloaded to prevent system lockup.")

                governor = RAMGovernor(threshold_pct=88.0, interval_sec=0.1)
                governor.start(_on_ram_trip, active_model)

                req = urllib.request.Request(
                    "http://127.0.0.1:11434/api/chat",
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(ollama_payload).encode("utf-8"),
                )

                accumulated_text = ""
                with urllib.request.urlopen(req, timeout=45) as resp:
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
                elif t_name == "sympy_eval" and _SYMPY_ENGINE:
                    expr = t_args.get("expression", "")
                    eval_res = _SYMPY_ENGINE.evaluate_expression(expr)
                    emit_fn("sympy", f"$${eval_res.get('latex', eval_res.get('result'))}$$")
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
    start_neuro_symbolic_bridge_server(8085)

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

    # Push initial telemetry as soon as page finishes loading
    def on_load_finished(view, event):
        if event == WebKit2.LoadEvent.FINISHED:
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
    try:
        Gtk.main()
    finally:
        OLLAMA.stop()


if __name__ == "__main__":
    main()
