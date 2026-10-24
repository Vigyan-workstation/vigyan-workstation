# 🏛️ Agent & Autonomous Contributor Guidelines (AGENTS.md)

Welcome, **Google Jules** and automated agent contributors! This document outlines the architectural rules, security boundaries, and verification procedures for contributing to **Vigyan Pro Desktop**.

---

## 1. System Vision & Architecture

**Vigyan Pro Desktop** is an air-gapped, zero-cloud physical engineering workstation designed to provide tactile, friction-free STEM tools (Parametric 3D CAD, 6-DoF Robotics Kinematics, WaveDrom Hardware Timing, KiCad PCB Netlists, and Verified Knowledge Graphs).

* **Shell**: Native WebKitGTK 4.1 (Linux) / WebView2 (Windows) / WKWebView (macOS).
* **Frontend**: Svelte 5 + Tailwind CSS (compiled into `src/dist/` using Bun / Vite).
* **Backend**: Python 3.14 neuro-symbolic bridge (`src/launch_desktop.py`).
* **Inference**: Air-gapped local Ollama daemon (`http://127.0.0.1:11434`).
* **Knowledge Graph**: Embedded C++ KùzuDB (`src/knowledge_graph/db_store.db`).
* **Math Core**: AST-whitelisted SymPy sandbox.

---

## 2. 🛑 Absolute Architectural Invariants (DO NOT BREAK)

When proposing changes, you MUST preserve the following core guarantees:

### 1. Air-Gapped Zero-Cloud Compliance
* **Never introduce external CDNs or remote URLs** (e.g. Google Fonts, unpkg, cdnjs, mathjax CDN).
* **No telemetry, crash-reporting, analytics, or remote API calls.** All fonts, scripts (KaTeX, Plotly, Three.js, WaveDrom), and models must remain 100% offline and bundled locally.

### 2. Linux System Package Coexistence (Crucial)
* In Linux environments, PyGObject (`gi`), `Gtk 3.0`, and `WebKit2 4.1` are provided by host OS packages (e.g. `/usr/lib/python3.14/site-packages`), NOT by PyPI.
* **Do NOT attempt to "fix" or replace `gi` imports with PyPI packages.**
* **Do NOT modify or remove the system site-packages auto-injection logic** in [`src/launch_desktop.py`](src/launch_desktop.py) or [`bin/vigyan-pro`](bin/vigyan-pro).

### 3. Zero-Node End-User Runtime
* End users running `./launch.sh` do not have Node.js installed.
* Any changes to `frontend/src/` **must be compiled into `src/dist/`** via `cd frontend && bun run build` so pre-built assets are always in sync.

### 4. Deterministic AST Security Sandbox
* Mathematical and calculus expressions are parsed through an AST whitelist in `src/launch_desktop.py` to prevent arbitrary code execution (`eval`/`exec`).
* Never bypass the AST whitelist or disable the session security token (`X-Vigyan-Token`).

### 5. Repository Cleanliness & File Size
* Do not commit duplicate database files or binary caches into Git. The verified database is `src/knowledge_graph/db_store.db`.

---

## 3. 🎯 High-Value Contributions Expected from Jules

Autonomous agents are encouraged to open PRs focusing on:

* **Security & Vulnerability Remediation**: Auditing `frontend/package.json` for npm CVEs and updating dependencies without breaking Svelte 5 runes.
* **Test Suite Expansion**: Adding new unit tests to [`tests/`](tests/) covering mathematical edge cases, OCR regex parsing, or hardware timing models.
* **Performance Optimizations**: Reducing latency in telemetry sysfs reads, optimizing WebGL draw calls, or improving Vite build bundling.
* **Typing & Code Hygiene**: Enhancing TypeScript interfaces in `frontend/src/lib/` and type hints in `src/tools/`.

---

## 4. 🧪 Mandatory Verification Checklist Before Opening a PR

Before submitting any Pull Request, ensure that:

1. **Python Unit Tests Pass**:
   ```bash
   pytest tests/
   ```
   *Expected:* 100% pass rate (all 35+ tests pass).
2. **Frontend Builds Cleanly**:
   ```bash
   cd frontend && bun run build
   ```
   *Expected:* Clean compilation in under 5 seconds with zero Vite/Svelte errors.
3. **No Unstaged or Stale Files**:
   Working tree must be clean with no orphan `__pycache__` or untracked test dumps.
4. **Descriptive PR Report**:
   Provide a concise markdown summary detailing what was changed, why it improves the workstation, and confirming that the Air-Gapped and WebKitGTK guarantees were preserved.
