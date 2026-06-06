#!/usr/bin/env bash
# Snowmaking Planner - one-step launcher for macOS / Linux.
# Creates a local virtual environment, installs dependencies, and runs the app.
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment (.venv)..."
  "$PY" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "Installing dependencies..."
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt

echo "Starting Snowmaking Planner..."
exec streamlit run app.py
