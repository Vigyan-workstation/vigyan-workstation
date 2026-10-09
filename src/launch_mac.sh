#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "========================================================"
echo "  Launching Vigyan Pro Sovereign Studio (macOS)"
echo "========================================================"

if command -v python3 &>/dev/null; then
    exec python3 "$DIR/launch_desktop_mac.py" "$@"
else
    INDEX_PATH="$DIR/index.html"
    open "file://$INDEX_PATH"
fi
