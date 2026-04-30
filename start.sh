#!/bin/bash
# SpectraAI Launcher
# Usage:
#   ./start.sh              — Run with splash screen
#   ./start.sh --no-splash  — Run without splash screen
#   ./start.sh --debug      — Run in debug mode

cd "$(dirname "$0")"

# Activate virtual environment
source .venv/bin/activate

# Clear bytecode cache to avoid stale .pyc issues
find src -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Launch SpectraAI
exec python3 run.py "$@"
