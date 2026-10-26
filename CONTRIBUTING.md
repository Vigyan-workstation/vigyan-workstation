# Contributing to Vigyan Workstation (ExperimentLab Community)

Welcome to the **Vigyan Workstation** open community! Vigyan Workstation is an air-gapped, zero-cloud physical engineering desktop application developed by **ExperimentLab AI** ([experimentlab.in](https://experimentlab.in)).

We welcome contributions from students, researchers, physical engineers, and open-source developers worldwide. To preserve our strict data sovereignty, security, and civilian ethics, all contributors must adhere to this guide.

---

## 1. 🛡️ Contributor License Agreement (CLA) & IP Ownership

By submitting a Pull Request, issue, patch, or code contribution to the **Vigyan Workstation** repository, you agree to the following terms:

1. **Assignment and Grant of Rights:**
   You grant **ExperimentLab AI** (`experimentlab.in`) and its founder an exclusive, perpetual, worldwide, irrevocable, royalty-free, transferable license (with full right to sublicense, commercialize, patent, or re-license) to all code, documentation, algorithms, and designs submitted in your contribution.
2. **Sole IP Ownership:**
   You acknowledge and agree that **ExperimentLab AI** retains sole, exclusive, and unencumbered ownership of all intellectual property, trademarks, patents, and copyrights in and to Vigyan Workstation.
3. **Originality & Authority:**
   You represent that your contribution is your original creation, does not infringe on third-party proprietary rights, and that you have full legal authority to grant this license.

---

## 2. 🛑 The Inviolable Core Principles

Every Pull Request must strictly respect these 4 architectural and ethical boundaries:

1. **Air-Gapped Zero-Cloud Guarantee:**
   - **Never introduce remote URLs, CDNs, or cloud telemetry.**
   - All scripts (KaTeX, Plotly, Three.js, WaveDrom), styles, fonts, and assets must be bundled locally.
2. **Demilitarized Civilian STEM Only:**
   - Vigyan Workstation is strictly for peaceful science, education, and civilian physical engineering.
   - PRs designed for weapons development, targeting systems, military intelligence, or warfare will be rejected immediately.
3. **Linux WebKitGTK & System Package Coexistence:**
   - PyGObject (`gi`), `Gtk 3.0`, and `WebKit2 4.1` must be loaded from host OS site-packages (`/usr/lib/python3*/site-packages`), NOT PyPI. Never remove or alter system site-packages auto-injection.
4. **Zero-Node User Runtime:**
   - End users do not have Node.js. If you edit `frontend/src/`, you **must compile it into `src/dist/`** using `cd frontend && bun run build`.

---

## 3. 🧪 Local Setup, Building & Testing

### Prerequisites (Linux)
```bash
# Ubuntu / Debian
sudo apt update
sudo apt install -y python3 python3-gi gir1.2-gtk-3.0 gir1.2-webkit2-4.1 curl
```

### 1-Click Launching
```bash
./launch.sh
```

### Frontend Development & Compilation
The frontend is built with **Svelte 5** and compiled via **Bun**:
```bash
cd frontend
bun install
bun run dev      # Local dev server
bun run build    # Compiles production assets into ../src/dist/
```

### Running the Test Suite
All 35 unit tests must pass before opening a PR:
```bash
pytest tests/
```

---

## 4. 🚀 Submitting a Pull Request

1. **Branch Naming:**
   - `feat/feature-name` (e.g. `feat/aerospace-airfoil-card`)
   - `fix/bug-name` (e.g. `fix/dh-matrix-precision`)
   - `perf/optimization` (e.g. `perf/sysfs-read-cache`)
2. **Pre-PR Checklist:**
   - [ ] All 35+ pytest unit tests pass (`pytest tests/`).
   - [ ] Frontend builds cleanly (`cd frontend && bun run build`).
   - [ ] Zero external network calls or remote CDNs added.
   - [ ] Monospace titanium aesthetic maintained (zero emojis in logs/UI).
   - [ ] I agree to the **Contributor License Agreement (CLA)** assigning IP to ExperimentLab AI.
3. Open your Pull Request against the `main` branch. The **ExperimentLab Community Manager** bot will review your PR and verify all tests.
