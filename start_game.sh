#!/usr/bin/env bash
# 🏏 Cricket 3D Game Simulator Launcher (Linux / macOS)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================"
echo "  🏏 3D Cricket Fielding & Bowling Simulation Game"
echo "======================================================================"
echo "Launching Python Physics & WebSocket Server (HTTP: 8080, WS: 8765)..."

python3 -m backend.game_server

