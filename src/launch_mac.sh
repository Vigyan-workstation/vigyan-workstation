#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "========================================================"
echo "  Launching Vigyan Pro Sovereign Studio (macOS)"
echo "========================================================"

for py_cmd in python3 /opt/homebrew/bin/python3 /usr/local/bin/python3 "$DIR/../.venv/bin/python3" "$DIR/.venv/bin/python3"; do
    if [ -x "$py_cmd" ] || command -v "$py_cmd" &>/dev/null; then
        exec "$py_cmd" "$DIR/launch_desktop_mac.py" "$@"
    fi
done

INDEX_PATH="$DIR/index.html"
echo "[WARN] Python 3 not detected. Opening UI directly (some offline agent features require Python 3)."
open "file://$INDEX_PATH"
