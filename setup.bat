@echo off
REM ============================================================================
REM  setup.bat — One-time setup for the AI-Powered Document Q&A System
REM
REM  Usage:   setup.bat
REM  Run from the project root (RAG_caddence/)
REM ============================================================================

echo.
echo ============================================
echo   DocQ^&A — Project Setup
echo ============================================
echo.

REM ── Check prerequisites ─────────────────────────────────────────────────────

where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not on PATH.
    echo         Install Python 3.11+ from https://www.python.org/downloads/
    exit /b 1
)

where node >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js is not installed or not on PATH.
    echo         Install Node.js 18+ from https://nodejs.org/
    exit /b 1
)

echo [OK] Python found:
python --version
echo [OK] Node.js found:
node --version
echo.

REM ── Backend Setup ───────────────────────────────────────────────────────────

echo --------------------------------------------
echo  1/3  Setting up Backend...
echo --------------------------------------------
echo.

cd backend

if not exist ".venv" (
    echo [INFO] Creating Python virtual environment...
    python -m venv .venv
) else (
    echo [INFO] Virtual environment already exists, skipping creation.
)

echo [INFO] Activating virtual environment...
call .venv\Scripts\activate.bat

echo [INFO] Installing Python dependencies...
pip install -r requirements.txt --quiet

if not exist ".env" (
    echo [INFO] Creating .env from .env.example...
    copy .env.example .env >nul
    echo.
    echo ========================================================
    echo  [ACTION REQUIRED] Edit backend\.env and set your
    echo  GOOGLE_API_KEY before running the application.
    echo ========================================================
    echo.
) else (
    echo [INFO] .env already exists, skipping.
)

if not exist "uploads" (
    mkdir uploads
    echo [INFO] Created uploads/ directory.
)

call deactivate 2>nul
cd ..

echo [OK] Backend setup complete.
echo.

REM ── Frontend Setup ──────────────────────────────────────────────────────────

echo --------------------------------------------
echo  2/3  Setting up Frontend...
echo --------------------------------------------
echo.

cd frontend

echo [INFO] Installing npm dependencies...
call npm install --silent

cd ..

echo [OK] Frontend setup complete.
echo.

REM ── Done ────────────────────────────────────────────────────────────────────

echo --------------------------------------------
echo  3/3  Setup Complete!
echo --------------------------------------------
echo.
echo  Next steps:
echo    1. Edit backend\.env and set your GOOGLE_API_KEY
echo    2. Run  run.bat  to start both servers
echo.
