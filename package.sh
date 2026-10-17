#!/usr/bin/env bash
# ==============================================================================
# Vigyan Pro Desktop - Multi-OS Release Packaging Script
# Builds packages for Linux (.deb, .tar.gz), Windows (.zip), and macOS (.tar.gz)
# Supports:
#   - Lightweight archives (~3.8 MB)
#   - Full Standalone Bundles with 1.1 GB Quad Master weights (--bundle-weights)
# ==============================================================================

set -e

RAW_VERSION="2.7.0"
BUNDLE_WEIGHTS=false

for arg in "$@"; do
    if [ "$arg" = "--bundle-weights" ] || [ "$arg" = "--bundled" ]; then
        BUNDLE_WEIGHTS=true
    elif [[ "$arg" =~ ^v?[0-9]+\.[0-9]+\.[0-9]+ ]]; then
        RAW_VERSION="$arg"
    fi
done

VERSION="${RAW_VERSION#v}"

echo "========================================================"
echo "  Building Vigyan Pro Multi-OS Desktop Release v${VERSION}"
if [ "$BUNDLE_WEIGHTS" = true ]; then
    echo "  Mode: Full Standalone Bundles (with 1.1GB Sovereign Model)"
else
    echo "  Mode: Standard Lightweight Packages"
fi
echo "========================================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DIST_DIR="$SCRIPT_DIR/dist"
mkdir -p "$DIST_DIR"

MODEL_SOURCE="$HOME/.vigyan/models/vigyan-1.5b-quad-master-q4_k_m.gguf"

# ------------------------------------------------------------------------------
# 1. BUILD DEBIAN (.deb) PACKAGE FOR LINUX
# ------------------------------------------------------------------------------
echo "==> Staging Debian package..."
DEB_STAGE="$SCRIPT_DIR/.build_deb"
rm -rf "$DEB_STAGE"

mkdir -p "$DEB_STAGE/DEBIAN"
mkdir -p "$DEB_STAGE/opt/vigyan-pro/src"
mkdir -p "$DEB_STAGE/opt/vigyan-pro/assets"
mkdir -p "$DEB_STAGE/opt/vigyan-pro/bin"
mkdir -p "$DEB_STAGE/usr/bin"
mkdir -p "$DEB_STAGE/usr/share/applications"
mkdir -p "$DEB_STAGE/usr/share/pixmaps"
mkdir -p "$DEB_STAGE/usr/share/icons/hicolor/64x64/apps"
mkdir -p "$DEB_STAGE/usr/share/icons/hicolor/128x128/apps"
mkdir -p "$DEB_STAGE/usr/share/icons/hicolor/256x256/apps"

# Copy application files
cp -r "$SCRIPT_DIR/src/"* "$DEB_STAGE/opt/vigyan-pro/src/"
cp -r "$SCRIPT_DIR/assets/"* "$DEB_STAGE/opt/vigyan-pro/assets/"
cp "$SCRIPT_DIR/bin/vigyan-pro" "$DEB_STAGE/opt/vigyan-pro/bin/vigyan-pro"
chmod +x "$DEB_STAGE/opt/vigyan-pro/bin/vigyan-pro"

# Symlink to /usr/bin/vigyan-pro
ln -s "/opt/vigyan-pro/bin/vigyan-pro" "$DEB_STAGE/usr/bin/vigyan-pro"

# Desktop Entry
cp "$SCRIPT_DIR/assets/vigyan-pro.desktop" "$DEB_STAGE/usr/share/applications/vigyan-pro.desktop"

# Icons
if [ -f "$SCRIPT_DIR/assets/icons/vigyan-pro-64.png" ]; then
    cp "$SCRIPT_DIR/assets/icons/vigyan-pro-64.png" "$DEB_STAGE/usr/share/icons/hicolor/64x64/apps/vigyan-pro.png"
fi
if [ -f "$SCRIPT_DIR/assets/icons/vigyan-pro-128.png" ]; then
    cp "$SCRIPT_DIR/assets/icons/vigyan-pro-128.png" "$DEB_STAGE/usr/share/icons/hicolor/128x128/apps/vigyan-pro.png"
fi
if [ -f "$SCRIPT_DIR/assets/icons/vigyan-pro-256.png" ]; then
    cp "$SCRIPT_DIR/assets/icons/vigyan-pro-256.png" "$DEB_STAGE/usr/share/icons/hicolor/256x256/apps/vigyan-pro.png"
    cp "$SCRIPT_DIR/assets/icons/vigyan-pro-256.png" "$DEB_STAGE/usr/share/pixmaps/vigyan-pro.png"
fi

# DEBIAN Control File
cat <<EOF > "$DEB_STAGE/DEBIAN/control"
Package: vigyan-pro
Version: ${VERSION}
Section: science
Priority: optional
Architecture: amd64
Maintainer: Shreyansh Lab <contact@experimentlab.in>
Depends: python3, python3-gi, gir1.2-gtk-3.0, gir1.2-webkit2-4.1, curl
Homepage: https://experimentlab.in
Description: Sovereign AI Studio with Spec-Driven Agents and Local Inference
 Vigyan Pro is an enterprise obsidian-grade sovereign desktop workstation
 featuring native KaTeX proofs, Plotly WebGL visualizations, and
 air-gapped local LLM inference via Ollama.
EOF

# DEBIAN postinst script
cat <<'EOF' > "$DEB_STAGE/DEBIAN/postinst"
#!/bin/sh
set -e
if which update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if which gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q /usr/share/icons/hicolor || true
fi
exit 0
EOF
chmod 755 "$DEB_STAGE/DEBIAN/postinst"

# DEBIAN postrm script
cat <<'EOF' > "$DEB_STAGE/DEBIAN/postrm"
#!/bin/sh
set -e
if which update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
exit 0
EOF
chmod 755 "$DEB_STAGE/DEBIAN/postrm"

DEB_OUTPUT="$DIST_DIR/vigyan-pro_${VERSION}_amd64.deb"

if which dpkg-deb >/dev/null 2>&1; then
    dpkg-deb --build --root-owner-group "$DEB_STAGE" "$DEB_OUTPUT"
else
    echo "==> dpkg-deb not found. Creating Debian package via universal ar/tar..."
    TMP_PKG="$SCRIPT_DIR/.deb_tmp"
    rm -rf "$TMP_PKG"
    mkdir -p "$TMP_PKG"
    echo "2.0" > "$TMP_PKG/debian-binary"
    tar -czf "$TMP_PKG/control.tar.gz" -C "$DEB_STAGE/DEBIAN" .
    tar -czf "$TMP_PKG/data.tar.gz" --exclude='./DEBIAN' -C "$DEB_STAGE" .
    (cd "$TMP_PKG" && ar rcs "$DEB_OUTPUT" debian-binary control.tar.gz data.tar.gz)
    rm -rf "$TMP_PKG"
fi

rm -rf "$DEB_STAGE"
echo "✓ Debian Package Built: $DEB_OUTPUT"

# ------------------------------------------------------------------------------
# 2. BUILD LINUX PORTABLE ARCHIVE (.tar.gz)
# ------------------------------------------------------------------------------
echo "==> Staging Portable Linux Archive..."
TAR_STAGE="$SCRIPT_DIR/.build_tar/vigyan-pro"
rm -rf "$SCRIPT_DIR/.build_tar"
mkdir -p "$TAR_STAGE"

cp -r "$SCRIPT_DIR/src" "$TAR_STAGE/"
cp -r "$SCRIPT_DIR/assets" "$TAR_STAGE/"
cp -r "$SCRIPT_DIR/bin" "$TAR_STAGE/"
chmod +x "$TAR_STAGE/bin/vigyan-pro"

cat <<'EOF' > "$TAR_STAGE/launch.sh"
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/bin/vigyan-pro" "$@"
EOF
chmod +x "$TAR_STAGE/launch.sh"

TAR_OUTPUT="$DIST_DIR/vigyan-pro_${VERSION}_linux_x86_64.tar.gz"
tar -czf "$TAR_OUTPUT" -C "$SCRIPT_DIR/.build_tar" vigyan-pro
echo "✓ Linux Lightweight Built: $TAR_OUTPUT"

if [ "$BUNDLE_WEIGHTS" = true ] && [ -f "$MODEL_SOURCE" ]; then
    echo "==> Bundling sovereign model into Linux Standalone package..."
    mkdir -p "$TAR_STAGE/models"
    cp "$MODEL_SOURCE" "$TAR_STAGE/models/"
    TAR_BUNDLED_OUTPUT="$DIST_DIR/vigyan-pro_${VERSION}_linux_x86_64_bundled.tar.gz"
    tar -czf "$TAR_BUNDLED_OUTPUT" -C "$SCRIPT_DIR/.build_tar" vigyan-pro
    echo "✓ Linux Standalone (with model) Built: $TAR_BUNDLED_OUTPUT"
fi
rm -rf "$SCRIPT_DIR/.build_tar"

# ------------------------------------------------------------------------------
# 3. BUILD WINDOWS PORTABLE ARCHIVE (.zip)
# ------------------------------------------------------------------------------
echo "==> Staging Portable Windows Archive..."
WIN_STAGE="$SCRIPT_DIR/.build_win/vigyan-pro"
rm -rf "$SCRIPT_DIR/.build_win"
mkdir -p "$WIN_STAGE"

cp -r "$SCRIPT_DIR/src" "$WIN_STAGE/"
cp -r "$SCRIPT_DIR/assets" "$WIN_STAGE/"

# Root launcher batch script
cat <<'EOF' > "$WIN_STAGE/Vigyan-Pro.bat"
@echo off
title Vigyan Pro
cd /d "%~dp0"
call src\launch_win.bat %*
EOF

WIN_OUTPUT="$DIST_DIR/vigyan-pro_${VERSION}_windows_x86_64.zip"
if which zip >/dev/null 2>&1; then
    (cd "$SCRIPT_DIR/.build_win" && zip -r -q "$WIN_OUTPUT" vigyan-pro)
else
    python3 -c "import shutil; shutil.make_archive('$DIST_DIR/vigyan-pro_${VERSION}_windows_x86_64', 'zip', '$SCRIPT_DIR/.build_win', 'vigyan-pro')"
fi
echo "✓ Windows Lightweight Built: $WIN_OUTPUT"

if [ "$BUNDLE_WEIGHTS" = true ] && [ -f "$MODEL_SOURCE" ]; then
    echo "==> Bundling sovereign model into Windows Standalone package..."
    mkdir -p "$WIN_STAGE/models"
    cp "$MODEL_SOURCE" "$WIN_STAGE/models/"
    WIN_BUNDLED_OUTPUT="$DIST_DIR/vigyan-pro_${VERSION}_windows_x86_64_bundled.zip"
    if which zip >/dev/null 2>&1; then
        (cd "$SCRIPT_DIR/.build_win" && zip -r -q "$WIN_BUNDLED_OUTPUT" vigyan-pro)
    else
        python3 -c "import shutil; shutil.make_archive('$DIST_DIR/vigyan-pro_${VERSION}_windows_x86_64_bundled', 'zip', '$SCRIPT_DIR/.build_win', 'vigyan-pro')"
    fi
    echo "✓ Windows Standalone (with model) Built: $WIN_BUNDLED_OUTPUT"
fi
rm -rf "$SCRIPT_DIR/.build_win"

# ------------------------------------------------------------------------------
# 4. BUILD MACOS PORTABLE ARCHIVE (.tar.gz)
# ------------------------------------------------------------------------------
echo "==> Staging Portable macOS Archive..."
MAC_STAGE="$SCRIPT_DIR/.build_mac/vigyan-pro"
rm -rf "$SCRIPT_DIR/.build_mac"
mkdir -p "$MAC_STAGE"

cp -r "$SCRIPT_DIR/src" "$MAC_STAGE/"
cp -r "$SCRIPT_DIR/assets" "$MAC_STAGE/"

cat <<'EOF' > "$MAC_STAGE/launch.sh"
#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$DIR/src/launch_mac.sh" "$@"
EOF
chmod +x "$MAC_STAGE/launch.sh"

cat <<'EOF' > "$MAC_STAGE/Vigyan-Pro.command"
#!/usr/bin/env bash
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$DIR/src/launch_mac.sh" "$@"
EOF
chmod +x "$MAC_STAGE/Vigyan-Pro.command"

MAC_OUTPUT="$DIST_DIR/vigyan-pro_${VERSION}_macos_universal.tar.gz"
tar -czf "$MAC_OUTPUT" -C "$SCRIPT_DIR/.build_mac" vigyan-pro
echo "✓ macOS Lightweight Built: $MAC_OUTPUT"

if [ "$BUNDLE_WEIGHTS" = true ] && [ -f "$MODEL_SOURCE" ]; then
    echo "==> Bundling sovereign model into macOS Standalone package..."
    mkdir -p "$MAC_STAGE/models"
    cp "$MODEL_SOURCE" "$MAC_STAGE/models/"
    MAC_BUNDLED_OUTPUT="$DIST_DIR/vigyan-pro_${VERSION}_macos_universal_bundled.tar.gz"
    tar -czf "$MAC_BUNDLED_OUTPUT" -C "$SCRIPT_DIR/.build_mac" vigyan-pro
    echo "✓ macOS Standalone (with model) Built: $MAC_BUNDLED_OUTPUT"
fi
rm -rf "$SCRIPT_DIR/.build_mac"

# ------------------------------------------------------------------------------
# 5. GENERATE CRYPTOGRAPHIC SHA-256 CHECKSUMS
# ------------------------------------------------------------------------------
echo "==> Generating Cryptographic SHA-256 Checksums for Enterprise Security Audit..."
(cd "$DIST_DIR" && sha256sum vigyan-pro_* > SHA256SUMS)
echo "✓ Enterprise SHA256SUMS generated:"
cat "$DIST_DIR/SHA256SUMS"

echo "========================================================"
echo "  Enterprise Multi-OS Packaging Complete!"
ls -lh "$DIST_DIR"
echo "========================================================"
