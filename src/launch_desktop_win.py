#!/usr/bin/env python3
"""
Vigyan Pro Sovereign Studio - Native Windows Desktop Launcher
Utilizes Microsoft Edge WebView2 on Windows 10/11 with zero browser chrome,
Smart Hybrid GPU+CPU Compute Engine, WMI/CUDA telemetry, and Neuro-Symbolic Bridge.
"""

import sys
import os
import subprocess

# Set Ollama hybrid compute acceleration flags before spawning daemon
os.environ.setdefault("OLLAMA_FLASH_ATTENTION", "1")
os.environ.setdefault("OLLAMA_KV_CACHE_TYPE", "q8_0")
os.environ.setdefault("OLLAMA_NUM_PARALLEL", "1")

try:
    import psutil
except ImportError:
    psutil = None


def get_windows_telemetry(mode: str = "auto") -> dict:
    """Detect Windows GPU (NVIDIA SMI or WMI VideoController), CPU physical cores, RAM, and battery."""
    logical_cores = os.cpu_count() or 4
    physical_cores = max(1, logical_cores // 2)
    ram_pct = 0.0
    cpu_pct = 0.0
    ram_total_gb = 8.0
    ram_avail_gb = 4.0
    on_battery = False
    battery_pct = 100
    is_laptop = False

    if psutil:
        try:
            logical_cores = psutil.cpu_count(logical=True) or logical_cores
            physical_cores = psutil.cpu_count(logical=False) or physical_cores
            vm = psutil.virtual_memory()
            ram_pct = float(vm.percent)
            ram_total_gb = round(vm.total / (1024 ** 3), 2)
            ram_avail_gb = round(vm.available / (1024 ** 3), 2)
            cpu_pct = float(psutil.cpu_percent(interval=None))
            if hasattr(psutil, "sensors_battery"):
                bat = psutil.sensors_battery()
                if bat is not None:
                    is_laptop = True
                    battery_pct = int(round(bat.percent))
                    on_battery = not bool(bat.power_plugged)
        except Exception:
            pass

    gpu_info = "CPU Only"
    has_gpu = False
    vram_total_mb = 0.0
    gpu_name = "Windows DirectML / CPU"

    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=0.35
        )
        if res.returncode == 0 and res.stdout.strip():
            parts = [p.strip() for p in res.stdout.strip().splitlines()[0].split(",")]
            if len(parts) >= 4:
                has_gpu = True
                gpu_name = parts[0]
                gpu_util = int(float(parts[1]))
                mem_used = float(parts[2])
                vram_total_mb = float(parts[3])
                gpu_info = f"GPU {gpu_util}% | {mem_used/1024:.1f}/{vram_total_mb/1024:.1f} GB"
    except Exception:
        pass

    if not has_gpu and sys.platform == "win32":
        try:
            res = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", "Name,AdapterRAM", "/format:csv"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=0.6
            )
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    cols = [c.strip() for c in line.strip().split(",")]
                    if len(cols) >= 3 and cols[2] and cols[2] != "Name":
                        has_gpu = True
                        gpu_name = cols[2]
                        try:
                            vram_total_mb = round(int(cols[1]) / (1024 ** 2), 1)
                        except Exception:
                            vram_total_mb = 2048.0
                        gpu_info = f"{gpu_name[:22]} ({vram_total_mb/1024:.1f} GB)"
                        break
        except Exception:
            pass

    num_thread = max(2, physical_cores - 1) if (mode == "cpu_eco" or on_battery) else physical_cores
    num_ctx = 4096 if ram_total_gb < 10 else 8192
    num_batch = 256 if ram_total_gb < 10 else 512
    num_gpu = 0 if (mode == "cpu_eco" or not has_gpu) else (99 if mode == "max_gpu" else (20 if vram_total_mb < 6000 else 99))

    return {
        "cpu_pct": cpu_pct,
        "cpu_percent": cpu_pct,
        "physical_cores": physical_cores,
        "cpu_cores_physical": physical_cores,
        "logical_cores": logical_cores,
        "cpu_cores_logical": logical_cores,
        "ram_pct": ram_pct,
        "ram_percent": ram_pct,
        "ram_total_gb": ram_total_gb,
        "ram_avail_gb": ram_avail_gb,
        "gpu_info": gpu_info,
        "gpu_available": has_gpu,
        "gpu_name": gpu_name,
        "compute_mode": mode,
        "strategy_label": f"Hybrid {mode.upper()} ({num_gpu}L GPU / {num_thread}C CPU)",
        "ollama_options": {
            "num_gpu": num_gpu,
            "num_thread": num_thread,
            "num_ctx": num_ctx,
            "num_batch": num_batch,
        },
        "power": {
            "is_laptop": is_laptop,
            "on_battery": on_battery,
            "battery_pct": battery_pct,
            "power_profile": f"Laptop {'Battery' if on_battery else 'AC'} ({battery_pct}%)" if is_laptop else "Desktop AC",
        },
        "hybrid": {
            "mode": mode,
            "num_gpu": num_gpu,
            "num_thread": num_thread,
            "num_ctx": num_ctx,
            "num_batch": num_batch,
        },
    }


def launch_webview2():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(base_dir, "index.html")
    icon_path = os.path.join(base_dir, "..", "assets", "micro_logo_v.ico")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(base_dir, "assets", "micro_logo_v.png")

    # Start embedded Neuro-Symbolic HTTP Bridge if available
    try:
        from launch_desktop import start_neuro_symbolic_bridge_server
        start_neuro_symbolic_bridge_server(8085)
    except Exception:
        pass

    # 1. Try pywebview with edgechromium (WebView2)
    try:
        import webview
        window = webview.create_window(
            title="Vigyan Pro",
            url=f"file:///{index_path.replace(os.sep, '/')}",
            width=1340,
            height=760,
            resizable=True,
            background_color='#000000',
            easy_drag=False
        )
        webview.start(gui='edgechromium', debug=False)
        return True
    except ImportError:
        pass
    except Exception as e:
        print(f"pywebview failed: {e}")

    # 2. Native Microsoft Edge App Mode Fallback (Installed on all Windows 10/11)
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe")
    ]
    edge_exe = next((p for p in edge_paths if os.path.exists(p)), "msedge.exe")

    file_url = f"file:///{index_path.replace(os.sep, '/')}"
    cmd = [
        edge_exe,
        f"--app={file_url}",
        "--window-size=1340,760",
        "--enable-features=OverlayScrollbar",
        "--force-dark-mode"
    ]
    try:
        proc = subprocess.Popen(cmd)
        proc.wait()
        return True
    except Exception as e:
        print(f"Failed to launch Edge app mode: {e}")
        import webbrowser
        webbrowser.open(file_url)
        return True


def _ollama_is_healthy() -> bool:
    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False


def main():
    try:
        from ollama_supervisor import OllamaSupervisor
        supervisor = OllamaSupervisor(["ollama", "serve"], is_healthy=_ollama_is_healthy)
        try:
            supervisor.start()
        except Exception as exc:
            print(f"[WARN] could not start ollama on windows: {exc}", file=sys.stderr)
        try:
            launch_webview2()
        finally:
            supervisor.stop()
    except ImportError:
        launch_webview2()


if __name__ == "__main__":
    main()
