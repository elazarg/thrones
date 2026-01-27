#!/usr/bin/env bash
# Setup script for isolated plugin virtual environments (Unix)
# Run from the project root: bash scripts/setup-plugins.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "Setting up plugin virtual environments..."

# --- Gambit plugin ---
GAMBIT_DIR="plugins/gambit"
if [ -d "$GAMBIT_DIR" ]; then
    echo ""
    echo "--- Gambit Plugin ---"
    if [ ! -d "$GAMBIT_DIR/venv" ]; then
        echo "Creating venv..."
        python3 -m venv "$GAMBIT_DIR/venv"
    fi
    echo "Installing dependencies..."
    "$GAMBIT_DIR/venv/bin/pip" install -e "$GAMBIT_DIR[dev]" --quiet
    echo "Gambit plugin ready."
else
    echo "Gambit plugin directory not found, skipping."
fi

# --- PyCID plugin ---
PYCID_DIR="plugins/pycid"
if [ -d "$PYCID_DIR" ]; then
    echo ""
    echo "--- PyCID Plugin ---"
    if [ ! -d "$PYCID_DIR/venv" ]; then
        echo "Creating venv..."
        python3 -m venv "$PYCID_DIR/venv"
    fi
    echo "Installing dependencies..."
    "$PYCID_DIR/venv/bin/pip" install -e "$PYCID_DIR[dev]" --quiet
    echo "PyCID plugin ready."
else
    echo "PyCID plugin directory not found, skipping."
fi

echo ""
echo "Plugin setup complete."
