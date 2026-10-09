# Enterprise Engineering & Contributing Guide — Vigyan Pro

Thank you for contributing to Vigyan Pro Desktop. To preserve the enterprise stability, cryptographic security, and air-gapped performance of this workstation, all contributions must strictly conform to these guidelines.

---

## 1. Architectural Philosophy

1. **Monochrome Obsidian Design System:**
   - Zero emojis anywhere in the user interface, logs, or commit messages.
   - 100% SVG hairline vector icons (Feather/Linear standard).
   - Pitch-black obsidian theme (`#000000`, `#08090d`, `#121520`).
2. **Air-Gapped Sovereign AI:**
   - Zero external telemetry or CDN calls at runtime.
   - All models strictly loaded through the sovereign Ollama daemon (`127.0.0.1:11434`).
   - Approved model families: `@shreyansh12183` and `@allenai` only.
3. **Multi-OS Parity:**
   - Features must operate equivalently across Linux (WebKitGTK 4.1), Windows (Edge WebView2), and macOS (Cocoa WKWebView).

---

## 2. Local Development & Testing

### Linux Prerequisites:
```bash
sudo apt update
sudo apt install -y python3 python3-gi gir1.2-gtk-3.0 gir1.2-webkit2-4.1 curl
```

### Launching in Development Mode:
```bash
# Launch directly from source
./bin/vigyan-pro
```

### Building Release Packages:
```bash
chmod +x package.sh
./package.sh 2.7.0
```

Verify that the distribution artifacts are generated in `./dist/`:
- `vigyan-pro_2.7.0_amd64.deb`
- `vigyan-pro_2.7.0_linux_x86_64.tar.gz`
- `vigyan-pro_2.7.0_windows_x86_64.zip`
- `vigyan-pro_2.7.0_macos_universal.tar.gz`
- `SHA256SUMS`

---

## 3. Pull Request Guidelines

1. **Branch Naming:**
   - `feat/feature-name`
   - `fix/security-or-bug-name`
   - `perf/optimization-name`
2. **Pre-Commit Checklist:**
   - [ ] No remote CDN URLs added to `index.html`.
   - [ ] Strict Content-Security-Policy preserved.
   - [ ] Markdown inputs sanitized via `escapeHtml()`.
   - [ ] Python launchers pass compilation: `python3 -m py_compile src/*.py`.
   - [ ] `package.sh` executes cleanly and generates matching `SHA256SUMS`.
3. Submit your PR with the standard pull request template.
