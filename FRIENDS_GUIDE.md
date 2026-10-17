# 🚀 Vigyan Pro — Friend's Quickstart Guide
*Sovereign Desktop STEM & Mathematical Intelligence Workstation • 100% Offline Edge Inference*

Welcome to **Vigyan Pro**! This software provides an air-gapped, zero-latency desktop workstation with LaTeX proofs, SymPy symbolic calculus, KùzuDB knowledge graphs, and the sovereign **Vigyan AI 1.5B Quad Master** model running locally on your hardware.

---

## ⚡ 3-Minute Quickstart by Operating System

### 🪟 Windows 10 / 11

1. **Prerequisite (One-time, 30 seconds)**:
   - Download and run the official installer from [ollama.com/download/windows](https://ollama.com/download/windows).
2. **Download & Extract**:
   - Download `vigyan-pro_windows_x86_64_bundled.zip` (or lightweight `.zip`).
   - Extract the folder anywhere on your computer (e.g. `Downloads` or `Desktop`).
3. **Launch**:
   - Double-click **`Vigyan-Pro.bat`**.
   - The app will automatically launch in native Microsoft Edge App Mode with zero browser chrome, register the model, and connect.

---

### 🍎 macOS (Intel & Apple Silicon M1/M2/M3/M4)

1. **Prerequisite (One-time)**:
   - Download the official Mac installer from [ollama.com/download/mac](https://ollama.com/download/mac) **or** run in Terminal:
     ```bash
     brew install ollama
     ```
2. **Download & Extract**:
   - Download `vigyan-pro_macos_universal_bundled.tar.gz` (or lightweight `.tar.gz`).
   - Double-click to extract the archive.
3. **Launch**:
   - Double-click **`Vigyan-Pro.command`** in Finder.
   - The native Apple Cocoa WKWebView desktop window will appear instantly.

---

### 🐧 Linux (Ubuntu, Debian, Fedora, Arch)

#### Option A: Native Debian/Ubuntu Package (`.deb`)
```bash
sudo dpkg -i vigyan-pro_2.7.0_amd64.deb
vigyan-pro
```

#### Option B: Standalone Portable Archive
1. Extract `vigyan-pro_linux_x86_64_bundled.tar.gz`:
   ```bash
   tar -xzf vigyan-pro_2.7.0_linux_x86_64_bundled.tar.gz
   cd vigyan-pro
   ```
2. Run:
   ```bash
   ./launch.sh
   ```

---

## 💡 What Makes Vigyan Pro Special?

- **100% Edge Privacy**: Everything runs directly on your CPU and GPU via local loopback (`http://127.0.0.1:8085`). Zero telemetry, zero corporate APIs, zero tracking.
- **Vigyan AI 1.5B Quad Master**: Fine-tuned sovereign model with deep mathematical reasoning, ChatML protocol, and zero hallucinations.
- **STEM Accelerators**: Press `Ctrl+T` to explore 20 pre-built accelerators across Electronics, Semiconductors, Physics, and Biology.
- **Command Palette**: Press `Ctrl+K` for instant command execution, memory cache eviction, and prompt workflows.
- **Mathematical Rigor**: Native KaTeX rendering for complex formulas and proofs inline.

---

## 🛠️ Troubleshooting

- **"Ollama Engine Offline" Banner**:
  - Make sure Ollama is running. Open your terminal or command prompt and type `ollama serve`. Click **Retry Connection** in the app.
- **RAM Optimization**:
  - Vigyan AI 1.5B Quad Master uses only ~1.1 GB of RAM and runs smoothly even on 8 GB laptops. To clear memory cache at any time, press `Ctrl+K` and select **Purge VRAM & RAM Cache**.

Enjoy your sovereign AI workstation!
*Architected and developed by Shreyansh Singh.*
