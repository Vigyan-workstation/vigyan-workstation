#!/usr/bin/env bash
# ==============================================================================
# Vigyan Pro Sovereign Studio - macOS Launcher & First-Run Bootstrap
# ==============================================================================
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "========================================================"
echo "  Launching Vigyan Pro Sovereign Studio (macOS)"
echo "  100% Offline Edge Intelligence • Shreyansh Singh"
echo "========================================================"

# Check if Ollama is installed
if ! command -v ollama &>/dev/null && [ ! -x "/opt/homebrew/bin/ollama" ] && [ ! -x "/usr/local/bin/ollama" ]; then
    echo ""
    echo "[!] Notice: Ollama is not detected on your Mac."
    echo "    Vigyan Pro runs 100% locally using Ollama."
    echo "    To install: brew install ollama   OR   visit https://ollama.com/download/mac"
    echo ""
fi

# Locate Python 3
for py_cmd in python3 /opt/homebrew/bin/python3 /usr/local/bin/python3 "$DIR/../.venv/bin/python3" "$DIR/.venv/bin/python3"; do
    if [ -x "$py_cmd" ] || command -v "$py_cmd" &>/dev/null; then
        exec "$py_cmd" "$DIR/launch_desktop_mac.py" "$@"
    fi
done

INDEX_PATH="$DIR/index.html"
echo "[WARN] Python 3 not detected. Opening UI directly in default browser..."
open "file://$INDEX_PATH"
