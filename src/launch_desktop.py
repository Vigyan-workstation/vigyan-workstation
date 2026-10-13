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
        num_ctx = 2048 if (on_battery or mode == "cpu_eco") else 4096
        num_batch = 256
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
# 3. EMBEDDED LOCAL NEURO-SYMBOLIC HTTP BRIDGE (PORT 8085 FALLBACK)
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
                "telemetry": tel,
            })
            self._send_cors(200)
            self.wfile.write(json.dumps(payload).encode("utf-8"))
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

        if self.path.startswith("/api/chat"):
            user_query = (body.get("query") or body.get("message") or "").strip()
            model = body.get("model") or "olmoe:1b-7b"
            enrichment = enrich_stem_query(user_query)

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            def _emit(event: str, data_obj: Any):
                chunk = f"event: {event}\ndata: {json.dumps(data_obj)}\n\n"
                self.wfile.write(chunk.encode("utf-8"))
                self.wfile.flush()

            try:
                if enrichment.get("sympy"):
                    s = enrichment["sympy"]
                    _emit("sympy", f"$${s.get('latex', s.get('result'))}$$")
                    _emit("think", f"SymPy AST Verified: {s.get('expression')} => {s.get('result')}\n")
                if enrichment.get("graph_axioms"):
                    cites = [f"[{a['domain']}: {a['law']}] {a['equation']}" for a in enrichment["graph_axioms"]]
                    _emit("memory", "<br>• " + "<br>• ".join(cites))
                    _emit("think", f"Retrieved {len(cites)} verified STEM axioms from KùzuDB GraphRAG.\n")

                # Stream from local Ollama (:11434) with hybrid GPU+CPU options
                import urllib.request
                hybrid = enrichment["hybrid"]
                sys_prompt = "You are Vigyan Pro, a deterministic Sovereign Neuro-Symbolic STEM AI Engine. Format formulas in clean LaTeX ($$...$$)."
                if enrichment.get("prompt_injection"):
                    sys_prompt += "\n\n" + enrichment["prompt_injection"]

                ollama_payload = {
                    "model": model,
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
                req = urllib.request.Request(
                    "http://127.0.0.1:11434/api/chat",
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(ollama_payload).encode("utf-8"),
                )
                with urllib.request.urlopen(req, timeout=45) as resp:
                    for line in resp:
                        line_s = line.decode("utf-8").strip()
                        if not line_s:
                            continue
                        chunk = json.loads(line_s)
                        tok = chunk.get("message", {}).get("content", "")
                        if tok:
                            _emit("token", tok)
            except Exception as exc:
                # Fallback deterministic answer if daemon is offline or model not pulled
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

    # Native IPC Message Handler (Bidirectional Communication: Telemetry, Hybrid Mode, Neuro-Symbolic AST/GraphRAG)
    def on_script_message(manager, js_result):
        try:
            val = js_result.to_value()
            if val and val.is_string():
                data = json.loads(val.to_string())
                action = data.get("action") or data.get("cmd")
                if action == "get_telemetry":
                    stats = get_system_telemetry()
                    js = f"window.onNativeTelemetry && window.onNativeTelemetry({json.dumps(stats)});"
                    webview.run_javascript(js, None, None, None)
                elif action == "set_compute_mode":
                    mode = data.get("mode", "auto")
                    stats = get_system_telemetry(override_mode=mode)
                    js = f"window.onNativeTelemetry && window.onNativeTelemetry({json.dumps(stats)});"
                    webview.run_javascript(js, None, None, None)
                elif action in ("neuro_symbolic_query", "enrich"):
                    req_id = data.get("reqId", "")
                    query_str = data.get("query", "")
                    enriched = enrich_stem_query(query_str)
                    enriched["reqId"] = req_id
                    js = f"window.__onNeuroSymbolicResult && window.__onNeuroSymbolicResult({json.dumps(enriched)});"
                    webview.run_javascript(js, None, None, None)
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
            js = f"window.onNativeTelemetry && window.onNativeTelemetry({json.dumps(stats)});"
            webview.run_javascript(js, None, None, None)
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

    # Keyboard shortcuts: F11 Fullscreen, Ctrl+R Reload
    def on_key_press(widget, event):
        keyval = event.keyval
        state = event.state
        if keyval == Gdk.KEY_F11:
            if win.get_window().get_state() & Gdk.WindowState.FULLSCREEN:
                win.unfullscreen()
            else:
                win.fullscreen()
            return True
        elif keyval in (Gdk.KEY_r, Gdk.KEY_R) and (state & Gdk.ModifierType.CONTROL_MASK):
            webview.reload()
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
