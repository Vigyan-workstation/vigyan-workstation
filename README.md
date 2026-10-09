# Vigyan Pro — Sovereign Desktop Workstation

> **Enterprise Obsidian-Grade Sovereign STEM & Legal AI Desktop Workstation**  
> *Zero browser chrome. 100% Native WebKitGTK desktop runtime. Offline KaTeX derivations & Plotly WebGL visualizations.*

---

## Overview

**Vigyan Pro Desktop** is a sovereign, privacy-preserving AI desktop workstation built for researchers, engineers, and legal scholars. Designed with an Apple macOS obsidian titanium aesthetic and a zero-emoji monochrome design system, it pairs real-time local neural models with native symbolic and visual STEM tooling.

```
┌──────────────────────────────────────────────────────────────┐
│  Vigyan Pro Desktop Shell (WebKitGTK / GTK3 / Wayland)       │
│  • Obsidian Pitch-Black Monochrome Design (#000000)          │
│  • Brushed Titanium Faceted "V" Micro-Glyph Branding         │
├──────────────────────────────────────────────────────────────┤
│  Triple Sovereign Workspace                                  │
│  • Studio: Real-time NDJSON streaming inference              │
│  • STEM Workbench: Native KaTeX proofs & Plotly WebGL plots  │
│  • Sovereign Vault: Curated @shreyansh12183 & @allenai catalog│
├──────────────────────────────────────────────────────────────┤
│  Local Sovereign Runtime                                     │
│  • Air-Gapped Ollama Daemon (127.0.0.1:11434)                │
│  • Offline Vendor Engine (KaTeX, Plotly, LocalStorage)       │
└──────────────────────────────────────────────────────────────┘
```

---

## Features

- **Apple macOS Permissive Design:** Clean SF Pro / Inter typography, pure obsidian background (`#000000`), subtle zinc hairline borders, and zero neon glows.
- **Zero-Emoji Monochrome Iconography:** Feather/Linear hairline vector line icons across all tabs, actions, and intent cards.
- **Real-Time NDJSON Streaming Inference:** Chunked token-by-token streaming with live Markdown and KaTeX rendering.
- **Curated Sovereign Model Vault:**
  - `Vidhi AI 1.5B (Legal Master)` (`@shreyansh12183 / Vidhi-AI-Instruct`)
  - `Vigyan 1.5B 4x-MoE (STEM Solver)` (`@shreyansh12183 / Vigyan-1.5B-4x-MoE`)
  - `OLMo2 7B PhD Pure Math` (`@shreyansh12183 / olmo2-7b-phd-pure-math`)
  - `OLMo2 7B Silicon RTL & EDA` (`@shreyansh12183 / olmo2-7b-silicon-rtl-eda`)
  - `OLMoE 1B-7B 64-Expert MoE` (`@allenai / OLMoE-1B-7B-0924`)
  - `OLMo 2 1B Instruct` (`@allenai / OLMo-2-0425-1B-Instruct`)
  - `Olmo 3 7B Instruct` (`@allenai / Olmo-3-7B-Instruct`)
- **Native STEM Workbench:**
  - 2D & 3D WebGL function visualization (Damped Wave, Gaussian Bell, Sigmoid, Fourier Square, 3D Sinc Ripple).
  - Step-by-step mathematical proof drawer with one-click LaTeX clipboard copying.
- **Multi-Session Local Persistence:** Complete offline session history, renaming, deletion, and markdown export.

---

## Installation & Packaging

### Option 1: Debian / Ubuntu (`.deb`)

Download `vigyan-pro_2.0.0_amd64.deb` from the [GitHub Releases](https://github.com/shreyansh001boy-tech/vigyan-pro-desktop/releases) and install via `apt`:

```bash
sudo apt install ./vigyan-pro_2.0.0_amd64.deb
```

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
