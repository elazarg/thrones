#!/bin/bash
# Restart the Game Theory Workbench backend server

set -e

echo "Stopping existing uvicorn processes..."
pkill -f "uvicorn app.main" 2>/dev/null || true

sleep 1

echo "Starting uvicorn server..."
cd "$(dirname "$0")/.."
.venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &

echo "Server starting on http://localhost:8000"
