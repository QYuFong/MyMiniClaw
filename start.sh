#!/usr/bin/env bash
# Mini-OpenClaw startup script (Linux / macOS)
# Uses Conda environment: miniclaw (Python 3.12)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "Mini-OpenClaw Startup Script"
echo "========================================"
echo ""

# --- Conda ---
if ! command -v conda &>/dev/null; then
  echo "[ERROR] Conda not found. Please install Anaconda or Miniconda and ensure 'conda' is on PATH."
  exit 1
fi

# shellcheck disable=SC1091
eval "$(conda shell.bash hook)"

MINICLAW_ENV="miniclaw"

if ! conda env list | awk '!/^#/ && NF {print $1}' | grep -qx "$MINICLAW_ENV"; then
  echo "[INFO] Conda environment '$MINICLAW_ENV' not found."
  echo "[INFO] Creating environment: conda create -n $MINICLAW_ENV python=3.12"
  conda create -n "$MINICLAW_ENV" python=3.12 -y
  echo "[INFO] Environment '$MINICLAW_ENV' created successfully."
else
  echo "[INFO] Conda environment '$MINICLAW_ENV' found."
fi

echo "[1/4] Activating Conda environment '$MINICLAW_ENV'..."
conda activate "$MINICLAW_ENV"
echo "[INFO] Conda environment '$MINICLAW_ENV' activated successfully."

# --- Node.js ---
if ! command -v node &>/dev/null; then
  echo "[ERROR] Node.js not found. Please install Node.js 18+."
  exit 1
fi

echo "[2/4] Checking backend environment..."
cd "$SCRIPT_DIR/backend"
if [ ! -f .env ]; then
  echo "[WARNING] .env file not found. Configure environment variables first."
  echo "Run: cp .env.example .env"
  echo "Then edit .env and add your API keys."
  exit 1
fi

echo "[3/4] Installing backend dependencies (in $MINICLAW_ENV)..."
if ! python -m pip show fastapi &>/dev/null; then
  echo "[INFO] Installing backend dependencies from requirements.txt..."
  python -m pip install -r requirements.txt
else
  echo "[INFO] Backend dependencies already installed (fastapi present)."
fi

echo "[4/4] Installing frontend dependencies..."
cd "$SCRIPT_DIR/frontend"
if [ ! -d node_modules ]; then
  echo "[INFO] Installing frontend dependencies..."
  npm install
else
  echo "[INFO] Frontend dependencies already installed."
fi

echo ""
echo "========================================"
echo "Starting services..."
echo "Backend: port 8002 (Conda env: $MINICLAW_ENV)"
echo "Frontend: port 3000"
echo "========================================"
echo ""

cleanup() {
  echo ""
  echo "[INFO] Shutting down..."
  if [ -n "${BACKEND_PID:-}" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [ -n "${FRONTEND_PID:-}" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  echo "[INFO] Goodbye."
  exit 0
}

trap cleanup INT TERM

cd "$SCRIPT_DIR/backend"
python -m uvicorn app:app --port 8002 --host 0.0.0.0 --reload &
BACKEND_PID=$!

sleep 2

cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "========================================"
echo "Startup complete!"
echo ""
echo "Local:   http://localhost:3000"
echo "LAN:     http://<YOUR_IP>:3000"
echo ""
echo "Note: Backend runs in Conda environment '$MINICLAW_ENV'."
echo "Press Ctrl+C to stop both services."
echo "========================================"

wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
