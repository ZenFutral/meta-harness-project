#!/usr/bin/env bash
# Meta-Harness 1-Click Startup Script for Linux / macOS

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if command -v python3 &>/dev/null; then
    PY_CMD="python3"
elif command -v python &>/dev/null; then
    PY_CMD="python"
else
    echo "[!] Error: Python 3 was not found in your PATH."
    exit 1
fi

"$PY_CMD" "$SCRIPT_DIR/start.py" "$@"
