#!/bin/bash
# macOS double-click helper to start the CragScrub GUI
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Allow running straight from the unpacked folder without installing the package
export PYTHONPATH="$SCRIPT_DIR/src:${PYTHONPATH}"

python -m cragscrub.gui "$@"
