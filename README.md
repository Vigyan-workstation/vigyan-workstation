# Vigyan Pro — Sovereign Desktop Workstation (v2.7.0)

[![CI - Multi-OS Verification](https://github.com/shreyansh001boy-tech/vigyan-pro-desktop/actions/workflows/ci.yml/badge.svg)](https://github.com/shreyansh001boy-tech/vigyan-pro-desktop/actions/workflows/ci.yml)
[![Security - Air Gapped Zero Egress](https://img.shields.io/badge/Security-Air--Gapped%20Zero--Egress-10b981.svg)](SECURITY.md)
[![License - Proprietary Commercial](https://img.shields.io/badge/License-Proprietary%20Enterprise-blue.svg)](LICENSE)
[![Platforms - Linux | Windows | macOS](https://img.shields.io/badge/Platforms-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey.svg)](#multi-platform-matrix)
[![Inference - Air-Gapped Local Daemon](https://img.shields.io/badge/Inference-127.0.0.1%3A11434-38bdf8.svg)](#local-sovereign-runtime)

> **Enterprise Obsidian-Grade Sovereign STEM & Semiconductor AI Desktop Workstation**  
> *Zero browser chrome. 100% Native cross-platform desktop runtime for Linux, Windows, and macOS.*  
> *Zero cloud egress. 100% Offline KaTeX derivations, Plotly WebGL 3D visualizations, and 60 FPS physics simulations.*

---

## 1. System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│  Vigyan Pro Desktop Shell (WebKitGTK Linux / WebView2 Win / Mac WKWeb) │
│  • Obsidian Pitch-Black Monochrome Design (#000000)                    │
│  • Strict Content Security Policy (connect-src 127.0.0.1:11434 only)   │
│  • Hardware-Accelerated WebGL & 2D Canvas Engines                      │
├────────────────────────────────────────────────────────────────────────┤
│  Triple Sovereign Workspace                                            │
│  • Studio: Multi-turn streaming calculus & symbolic STEM dialogue      │
│  • STEM Workbench: 2D Plotter, 3D CAD/Molecules & 60 FPS Simulations   │
│  • Sovereign Vault: Curated @shreyansh12183 & @allenai model hub       │
├────────────────────────────────────────────────────────────────────────┤
│  Domain-Specialized Scientific Workspaces                              │
│  • Lab Studio · Semiconductor · Astronomy · Biomed · Chemistry        │
├────────────────────────────────────────────────────────────────────────┤
│  Local Sovereign Runtime & Security Boundary                           │
│  • Air-Gapped Local Daemon (http://127.0.0.1:11434)                    │
│  • Offline Vendor Assets (Bundled KaTeX, Plotly WebGL, MathJax-free)   │
│  • Cryptographic Release Verification (SHA256SUMS)                     │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Enterprise Security Architecture

Vigyan Pro Desktop is architected for strict data sovereignty, intelligence research, and semiconductor IP protection:

* **Zero Cloud Egress:** Client runtime initiates zero connections outside `127.0.0.1:11434`. No telemetry, analytics, crash pings, or font CDNs.
* **Strict Content Security Policy (CSP):**
  ```http
  default-src 'self' file: data: blob: http://127.0.0.1:11434 http://localhost:11434;
  script-src 'self' 'unsafe-inline' 'unsafe-eval' file: blob:;
  connect-src 'self' http://127.0.0.1:11434 http://localhost:11434;
  object-src 'none'; frame-src 'none'; base-uri 'self'; form-action 'none';
  ```
* **Input/Output Sanitization:** All prompt queries and streaming model outputs pass through strict HTML entity encoding prior to LaTeX compilation, neutralizing DOM injection and Cross-Site Scripting (XSS).
* **Restricted Navigation Handlers:** WebKitGTK and WebView2 intercept all navigation requests (`decide-policy`). Arbitrary URLs cannot be loaded inside the application window.
* **Supply Chain Cryptographic Verification:** All build artifacts are signed and published with cryptographic SHA-256 hashes (`SHA256SUMS`).

For complete threat models and reporting procedures, read [SECURITY.md](SECURITY.md).

---

## 3. Multi-Platform Matrix & System Requirements

| OS | Desktop Engine | Min Requirements | Recommended Hardware |
| :--- | :--- | :--- | :--- |
| **Linux** | WebKitGTK 4.1 (`gir1.2-webkit2-4.1`) | Ubuntu 20.04+, Debian 11+, Arch, Fedora | 16 GB RAM, NVIDIA/AMD GPU, 4 cores |
| **Windows** | Microsoft Edge WebView2 | Windows 10/11 x64 (Build 19041+) | 16 GB RAM, RTX 3060+, 4 cores |
| **macOS** | Apple Cocoa WKWebView | macOS 12 Monterey+ (Universal M-Series / Intel) | 16 GB Unified Memory (Apple Silicon) |

---

## 4. Multi-Device Installation & Verification

Download official release packages from the [Private GitHub Releases](https://github.com/shreyansh001boy-tech/vigyan-pro-desktop/releases):

### Linux (Debian / Ubuntu / Pop!_OS / Mint)
```bash
# 1. Download deb package and checksum file
wget https://github.com/shreyansh001boy-tech/vigyan-pro-desktop/releases/download/v2.7.0/vigyan-pro_2.7.0_amd64.deb
wget https://github.com/shreyansh001boy-tech/vigyan-pro-desktop/releases/download/v2.7.0/SHA256SUMS

# 2. Verify Cryptographic Integrity
sha256sum --check --ignore-missing SHA256SUMS

# 3. Install
sudo apt install ./vigyan-pro_2.7.0_amd64.deb

# 4. Launch from desktop application menu or terminal
vigyan-pro
```

### Linux Portable (Arch, Fedora, openSUSE, RHEL)
```bash
tar -xzf vigyan-pro_2.7.0_linux_x86_64.tar.gz
cd vigyan-pro-2.7.0
./vigyan-pro
```

### Windows 10 / 11
1. Extract `vigyan-pro_2.7.0_windows_x86_64.zip`.
2. Double-click `Vigyan-Pro.bat` or run from PowerShell:
   ```powershell
   .\Vigyan-Pro.bat
   ```

### macOS (Apple Silicon & Intel)
1. Extract `vigyan-pro_2.7.0_macos_universal.tar.gz`.
2. Right-click `Vigyan-Pro.command` and select **Open**:
   ```bash
   ./Vigyan-Pro.command
   ```

---

## 5. STEM Scientific Workbench Capabilities

1. **2D Dynamic Function Plotter:**
   * Dual-trace comparative plotting ($f_1(x)$ primary white trace, $f_2(x)$ secondary cyan trace).
   * Real-time numerical calculus: live derivative curve ($f'(x)$ in amber) and cumulative numerical integral curve ($\int f(x)dx$ in emerald).
   * Real-time cursor coordinates HUD readout `(x, y)`.
   * Presets: MOSFET Saturation, Shockley Diode $I\text{-}V$, Damped Oscillator, Soliton Wave ($sech^2$), Gaussian Normal, Sigmoid, Fourier Square, and Bessel $J_0(x)$.
2. **3D CAD & Molecular Structure Suite:**
   * Interactive WebGL crystal and molecular rendering: Graphene Monolayer ($sp^2$ hexagonal carbon sheet), Caffeine ($C_8H_{10}N_4O_2$), Silicon Diamond Cubic Lattice ($Fd\bar{3}m$), Benzene ($C_6H_6$), Water ($H_2O$), Methane ($CH_4$), Torus, Spring, and Paraboloid.
   * Isometric, Top, and Front projections with Wireframe toggle.
3. **60 FPS Dynamic Simulation Engine:**
   * Quantum Tunneling & Wavepacket Dispersion with barrier height slider $V_0$, live transmission ($T$) and reflection ($R$) coefficients.
   * PN Junction Band Bending ($E_c, E_v, E_F, W_{dep}$) with real-time bias control.
   * Coupled Double Pendulum, Keplerian Orbits, Michaelis-Menten Enzyme Kinetics, and Reversible Chemical Equilibrium.

---

## 6. Curated Sovereign Model Vault

Models strictly sourced from verified sovereign checkpoints (`@shreyansh12183` and `@allenai`):

| Model Name | HuggingFace / Ollama Identifier | Architecture | Domain |
| :--- | :--- | :--- | :--- |
| **OLMoE 1B-7B MoE** | `@allenai/OLMoE-1B-7B-0924` | 64 Sparse Experts (1B active) | Multidisciplinary STEM |
| **Vigyan 1.5B 4x-MoE** | `@shreyansh12183/Vigyan-1.5B-4x-MoE` | Sparse MoE Top-2 Routing | Calculus & Physics Solver |
| **OLMo2 7B Pure Math** | `@shreyansh12183/olmo2-7b-phd-pure-math` | Dense 7B Full Precision | Doctoral Proofs & Real Analysis |
| **OLMo2 7B Silicon EDA** | `@shreyansh12183/olmo2-7b-silicon-rtl-eda` | Dense 7B Instruction | Verilog RTL & VLSI Synthesis |
| **OLMo 2 1B Instruct** | `@allenai/OLMo-2-0425-1B-Instruct` | Dense 1B Low-Latency | Low-Power Embedded Edge |
| **Olmo 3 7B Instruct** | `@allenai/Olmo-3-7B-Instruct` | Dense 7B Sovereign | General Advanced Science |

---

## 7. Packaging & Building from Source

```bash
# Build multi-OS distribution packages and generate SHA256SUMS
chmod +x package.sh
./package.sh 2.7.0
```

All distribution packages are placed in `./dist/`:
```
dist/
├── SHA256SUMS
├── vigyan-pro_2.7.0_amd64.deb
├── vigyan-pro_2.7.0_linux_x86_64.tar.gz
├── vigyan-pro_2.7.0_macos_universal.tar.gz
└── vigyan-pro_2.7.0_windows_x86_64.zip
```

---

## 8. License

Proprietary Commercial Software — Copyright © 2026 Shreyansh Lab. All Rights Reserved. See [LICENSE](LICENSE) for terms.
