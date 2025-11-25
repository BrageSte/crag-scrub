#!/bin/bash
# macOS double-click helper to start the CragScrub GUI
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1
python -m cragscrub.gui "$@"
