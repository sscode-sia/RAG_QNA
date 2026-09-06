#!/usr/bin/env bash
# =============================================================================
#  setup.sh — One-time setup for the AI-Powered Document Q&A System
#
#  Usage:   chmod +x setup.sh && ./setup.sh
#  Run from the project root (RAG_caddence/)
# =============================================================================

set -e

echo ""
echo "============================================"
echo "  DocQ&A — Project Setup"
echo "============================================"
echo ""

# ── Check prerequisites ──────────────────────────────────────────────────────

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed."
    echo "        Install Python 3.11+ from https://www.python.org/downloads/"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js is not installed."
    echo "        Install Node.js 18+ from https://nodejs.org/"
    exit 1
fi

echo "[OK] Python found: $(python3 --version)"
echo "[OK] Node.js found: $(node --version)"
echo ""

# ── Backend Setup ─────────────────────────────────────────────────────────────

echo "--------------------------------------------"
echo " 1/3  Setting up Backend..."
echo "--------------------------------------------"
echo ""

cd backend

if [ ! -d ".venv" ]; then
    echo "[INFO] Creating Python virtual environment..."
    python3 -m venv .venv
else
    echo "[INFO] Virtual environment already exists, skipping creation."
fi

echo "[INFO] Activating virtual environment..."
source .venv/bin/activate

echo "[INFO] Installing Python dependencies..."
pip install -r requirements.txt --quiet

if [ ! -f ".env" ]; then
    echo "[INFO] Creating .env from .env.example..."
    cp .env.example .env
    echo ""
    echo "========================================================"
    echo " [ACTION REQUIRED] Edit backend/.env and set your"
    echo " GOOGLE_API_KEY before running the application."
    echo "========================================================"
    echo ""
else
    echo "[INFO] .env already exists, skipping."
fi

mkdir -p uploads
deactivate 2>/dev/null || true

cd ..

echo "[OK] Backend setup complete."
echo ""

# ── Frontend Setup ────────────────────────────────────────────────────────────

echo "--------------------------------------------"
echo " 2/3  Setting up Frontend..."
echo "--------------------------------------------"
echo ""

cd frontend

echo "[INFO] Installing npm dependencies..."
npm install --silent

cd ..

echo "[OK] Frontend setup complete."
echo ""

# ── Done ──────────────────────────────────────────────────────────────────────

echo "--------------------------------------------"
echo " 3/3  Setup Complete!"
echo "--------------------------------------------"
echo ""
echo " Next steps:"
echo "   1. Edit backend/.env and set your GOOGLE_API_KEY"
echo "   2. Run  ./run.sh  to start both servers"
echo ""
