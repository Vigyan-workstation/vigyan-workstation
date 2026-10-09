#!/usr/bin/env bash
# ==============================================================================
# Vigyan Pro Desktop - Automated Release Packaging Script
# Builds native Debian (.deb) package and standalone portable (.tar.gz) bundle
# ==============================================================================

set -e

RAW_VERSION="${1:-2.0.0}"
VERSION="${RAW_VERSION#v}"

echo "========================================================"
echo "  Building Vigyan Pro Desktop Release v${VERSION}"
echo "========================================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DIST_DIR="$SCRIPT_DIR/dist"
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

# ------------------------------------------------------------------------------
# 1. BUILD DEBIAN (.deb) PACKAGE
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
    
    # Control tarball
    tar -czf "$TMP_PKG/control.tar.gz" -C "$DEB_STAGE/DEBIAN" .
    
    # Data tarball
    tar -czf "$TMP_PKG/data.tar.gz" --exclude='./DEBIAN' -C "$DEB_STAGE" .
    
    # Pack into .deb using ar
    (cd "$TMP_PKG" && ar rcs "$DEB_OUTPUT" debian-binary control.tar.gz data.tar.gz)
    rm -rf "$TMP_PKG"
fi

rm -rf "$DEB_STAGE"
echo "✓ Debian Package Built: $DEB_OUTPUT"

# ------------------------------------------------------------------------------
# 2. BUILD PORTABLE STANDALONE ARCHIVE (.tar.gz)
# ------------------------------------------------------------------------------
echo "==> Staging Portable Archive..."
TAR_STAGE="$SCRIPT_DIR/.build_tar/vigyan-pro"
rm -rf "$SCRIPT_DIR/.build_tar"
mkdir -p "$TAR_STAGE"

cp -r "$SCRIPT_DIR/src" "$TAR_STAGE/"
cp -r "$SCRIPT_DIR/assets" "$TAR_STAGE/"
cp -r "$SCRIPT_DIR/bin" "$TAR_STAGE/"
chmod +x "$TAR_STAGE/bin/vigyan-pro"

# Quick launcher in root of archive
cat <<'EOF' > "$TAR_STAGE/launch.sh"
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/bin/vigyan-pro" "$@"
EOF
chmod +x "$TAR_STAGE/launch.sh"

TAR_OUTPUT="$DIST_DIR/vigyan-pro_${VERSION}_linux_x86_64.tar.gz"
tar -czf "$TAR_OUTPUT" -C "$SCRIPT_DIR/.build_tar" vigyan-pro
rm -rf "$SCRIPT_DIR/.build_tar"
echo "✓ Portable Archive Built: $TAR_OUTPUT"

echo "========================================================"
echo "  Packaging Complete!"
ls -lh "$DIST_DIR"
echo "========================================================"
