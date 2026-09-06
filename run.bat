@echo off
REM ============================================================================
REM  run.bat — Start both backend and frontend servers
REM
REM  Usage:   run.bat
REM  Run from the project root (RAG_caddence/)
REM
REM  This opens two separate terminal windows:
REM    - Backend  → http://localhost:8000  (API + Swagger at /docs)
REM    - Frontend → http://localhost:3000  (Web UI)
REM ============================================================================

echo.
echo ============================================
echo   DocQ^&A — Starting Servers
echo ============================================
echo.

REM ── Verify setup ────────────────────────────────────────────────────────────

if not exist "backend\.venv" (
    echo [ERROR] Backend virtual environment not found.
    echo         Run  setup.bat  first.
    exit /b 1
)

if not exist "frontend\node_modules" (
    echo [ERROR] Frontend dependencies not installed.
    echo         Run  setup.bat  first.
    exit /b 1
)

if not exist "backend\.env" (
    echo [ERROR] backend\.env not found.
    echo         Run  setup.bat  first, then edit .env with your GOOGLE_API_KEY.
    exit /b 1
)

REM ── Start Backend (new window) ──────────────────────────────────────────────

echo [INFO] Starting Backend server (port 8000)...
start "DocQ&A — Backend" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && echo. && echo [Backend] Running on http://localhost:8000 && echo [Backend] Swagger UI at http://localhost:8000/docs && echo. && uvicorn main:app --reload --port 8000"

REM ── Start Frontend (new window) ─────────────────────────────────────────────

echo [INFO] Starting Frontend server (port 3000)...
start "DocQ&A — Frontend" cmd /k "cd /d %~dp0frontend && echo. && echo [Frontend] Running on http://localhost:3000 && echo. && npm run dev"

echo.
echo ============================================
echo   Both servers are starting!
echo ============================================
echo.
echo   Backend  : http://localhost:8000
echo   Swagger  : http://localhost:8000/docs
echo   Frontend : http://localhost:3000
echo.
echo   Close the terminal windows to stop the servers.
echo.

REM ── Auto-open browser after a short delay ───────────────────────────────────

timeout /t 5 /nobreak >nul
start http://localhost:3000
