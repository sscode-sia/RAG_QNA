#!/usr/bin/env bash
# =============================================================================
#  run.sh — Start both backend and frontend servers
#
#  Usage:   chmod +x run.sh && ./run.sh
#  Run from the project root (RAG_caddence/)
#
#  Starts both servers as background processes. Press Ctrl+C to stop both.
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "============================================"
echo "  DocQ&A — Starting Servers"
echo "============================================"
echo ""

# ── Verify setup ─────────────────────────────────────────────────────────────

if [ ! -d "$SCRIPT_DIR/backend/.venv" ]; then
    echo "[ERROR] Backend virtual environment not found."
    echo "        Run  ./setup.sh  first."
    exit 1
fi

if [ ! -d "$SCRIPT_DIR/frontend/node_modules" ]; then
    echo "[ERROR] Frontend dependencies not installed."
    echo "        Run  ./setup.sh  first."
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/backend/.env" ]; then
    echo "[ERROR] backend/.env not found."
    echo "        Run  ./setup.sh  first, then edit .env with your GOOGLE_API_KEY."
    exit 1
fi

# ── Cleanup function ─────────────────────────────────────────────────────────

cleanup() {
    echo ""
    echo "[INFO] Shutting down servers..."
    kill "$BACKEND_PID" 2>/dev/null || true
    kill "$FRONTEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
    wait "$FRONTEND_PID" 2>/dev/null || true
    echo "[OK] All servers stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM

# ── Start Backend ─────────────────────────────────────────────────────────────

echo "[INFO] Starting Backend server (port 8000)..."
(
    cd "$SCRIPT_DIR/backend"
    source .venv/bin/activate
    uvicorn main:app --reload --port 8000
) &
BACKEND_PID=$!

# ── Start Frontend ────────────────────────────────────────────────────────────

echo "[INFO] Starting Frontend server (port 3000)..."
(
    cd "$SCRIPT_DIR/frontend"
    npm run dev
) &
FRONTEND_PID=$!

echo ""
echo "============================================"
echo "  Both servers are running!"
echo "============================================"
echo ""
echo "  Backend  : http://localhost:8000"
echo "  Swagger  : http://localhost:8000/docs"
echo "  Frontend : http://localhost:3000"
echo ""
echo "  Press Ctrl+C to stop both servers."
echo ""

# ── Auto-open browser (optional, works on macOS & Linux) ─────────────────────

sleep 4
if command -v open &> /dev/null; then
    open http://localhost:3000
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:3000
fi

# ── Wait for both processes ───────────────────────────────────────────────────

wait
