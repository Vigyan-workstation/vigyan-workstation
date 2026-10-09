# Vigyan Pro — Sovereign Desktop Workstation (v2.6.0)

> **Enterprise Obsidian-Grade Sovereign STEM & Semiconductor AI Desktop Workstation**  
> *Zero browser chrome. 100% Native cross-platform desktop runtime for Linux, Windows, and macOS.*  
> *Offline KaTeX derivations, Plotly WebGL 3D visualizations, and 60 FPS physics simulations.*

---

## Overview

**Vigyan Pro Desktop** is a sovereign, privacy-preserving AI workstation designed for researchers, computational physicists, and hardware/semiconductor engineers. Built with a pitch-black obsidian aesthetic (`#000000`) and a zero-emoji monochrome design system, it couples local neural inference with native mathematical, simulation, and 3D CAD tooling.

```
┌──────────────────────────────────────────────────────────────┐
│  Vigyan Pro Shell (WebKitGTK Linux / WebView2 Win / Mac)     │
│  • High-Contrast Obsidian Pitch-Black Monochrome Design      │
│  • Brushed Titanium Faceted "V" Micro-Glyph Branding         │
├──────────────────────────────────────────────────────────────┤
│  Triple Sovereign Workspace                                  │
│  • Studio: Multi-turn streaming calculus & STEM dialogue     │
│  • STEM Workbench: 2D Plotter, 3D CAD/Molecules & 60 FPS Sim │
│  • Sovereign Vault: Curated @shreyansh12183 & @allenai models│
├──────────────────────────────────────────────────────────────┤
│  Specialized Scientific Workspaces                           │
│  • Lab Studio · Semiconductor · Astronomy · Biomed · Chem    │
├──────────────────────────────────────────────────────────────┤
│  Local Sovereign Runtime                                     │
│  • Air-Gapped Ollama Daemon (127.0.0.1:11434)                │
│  • Offline Vendor Engines (KaTeX, Plotly WebGL, Canvas 2D)   │
└──────────────────────────────────────────────────────────────┘
```

---

## Features

- **Multi-OS Native Workstation:** Linux (WebKitGTK 4.1), Windows (Microsoft Edge WebView2), macOS (Apple Cocoa WKWebView).
- **High-Contrast Dark Theme Engine:**
  - Pitch-black obsidian containers (`#08090d` / `#121520`) with pure white typography (`#ffffff` / `#e2e8f0`).
  - Zero native WebKit white-box artifacts with custom hairline SVG chevron selectors.
  - Generous bottom scroll padding preventing any occlusion by the floating navigation dock.
- **Advanced STEM Workbench:**
  - **2D Dynamic Function Plotter:** Dual trace plotting ($f_1(x)$ and $f_2(x)$), live real-time numerical derivative ($f'(x)$) and numerical cumulative integral ($\int f(x)dx$), interactive coordinate readout, dynamic frequency/damping/offset sliders, and scientific presets (MOSFET, Shockley diode, Damped oscillator, Soliton wave, Gaussian normal, Sigmoid, Bessel $J_0$).
  - **3D CAD & Molecular Structure Suite:** WebGL interactive rendering for Graphene Monolayer ($sp^2$ hexagonal carbon lattice), Caffeine ($C_8H_{10}N_4O_2$), Silicon Diamond Lattice ($Fd\bar{3}m$), Benzene ($C_6H_6$), Water ($H_2O$), Methane ($CH_4$), Torus, Spring, and Paraboloid with camera angle controls and wireframe mode.
  - **60 FPS Dynamic Simulation Engine:** Quantum tunneling wavepacket dispersion across variable potential barrier $V_0$ with real-time transmission $T$ and reflection $R$ coefficients, PN junction band bending with interactive voltage bias, coupled double pendulum, Keplerian celestial orbits, Michaelis-Menten enzyme kinetics, and reversible chemical equilibrium.
- **Uncluttered Sovereign Vault:**
  - `OLMoE 1B-7B MoE` (`@allenai / OLMoE-1B-7B-0924`) — 64 Sparse Experts, 1B Active/token.
  - `Vigyan 1.5B 4x-MoE` (`@shreyansh12183 / Vigyan-1.5B-4x-MoE`) — Calculus & physics solver.
  - `OLMo2 7B Pure Math` (`@shreyansh12183 / olmo2-7b-phd-pure-math`) — Doctoral real analysis.
  - `OLMo2 7B Silicon EDA` (`@shreyansh12183 / olmo2-7b-silicon-rtl-eda`) — ASIC Verilog RTL.
  - `OLMo 2 1B Instruct` (`@allenai / OLMo-2-0425-1B-Instruct`) — Low-latency inference.
  - `Olmo 3 7B Instruct` (`@allenai / Olmo-3-7B-Instruct`) — Multidisciplinary science.
- **Luxury Glassmorphic Settings:**
  - Model memory cache keep-alive timeout control.
  - Segmented reasoning profiles (Deterministic Proof, Balanced Analysis, Exploratory Synthesis).
  - Dynamic context buffer slider with live VRAM allocation progress meter.
  - Precision sampling controls and system persona directives.
- **Zero-Emoji Monochrome Iconography:** Hairline vector line icons across all tabs, actions, and intent cards.
- **Multi-Turn Context Ingestion:** Rolling message buffer retaining formulas and derivation steps across conversational turns.

---

## Installation & Packaging

Download the latest release assets from the [GitHub Releases](https://github.com/shreyansh001boy-tech/vigyan-pro-desktop/releases):

### Linux (`.deb` or Standalone Archive)
```bash
# Debian / Ubuntu
sudo apt install ./vigyan-pro_2.6.0_amd64.deb

# Portable Archive
tar -xzf vigyan-pro_2.6.0_linux_x86_64.tar.gz
cd vigyan-pro-2.6.0 && ./vigyan-pro
```

### Windows
Extract `vigyan-pro_2.6.0_windows_x86_64.zip` and double-click `Vigyan-Pro.bat`.

### macOS
Extract `vigyan-pro_2.6.0_macos_universal.tar.gz` and execute `./Vigyan-Pro.command`.

Run directly from your application launcher or terminal:
```bash
vigyan-pro
```

### Option 2: Portable Archive (`.tar.gz`)

Download and extract the standalone tarball:

```bash
tar -xzf vigyan-pro_2.0.0_linux_x86_64.tar.gz
cd vigyan-pro
./launch.sh
```

---

## Building from Source

Ensure GTK 3 and WebKit2 are installed:

```bash
# Ubuntu / Debian
sudo apt install python3 python3-gi gir1.2-gtk-3.0 gir1.2-webkit2-4.1 curl

# Arch Linux
sudo pacman -S python-gobject gtk3 webkit2gtk-4.1 curl
```

Build the release distribution packages:
```bash
chmod +x package.sh
./package.sh 2.0.0
```

Release packages will be generated inside `./dist/`.

---

## Automated CI/CD Releases

Releases are automatically built and published via GitHub Actions on every semantic git tag push (`v*.*.*`).

---

## License

Proprietary — © 2026 Shreyansh Lab. All Rights Reserved.
