@echo off
setlocal

REM =================================================================
REM  A.R.G.U.S. - Final Production Startup Script (with venv)
REM =================================================================
REM  - Activates the dedicated Python virtual environment.
REM  - Fixes all library conflict issues.
REM  - This is the standard and most reliable way to run Python apps.
REM =================================================================

REM --- Get the directory of this batch file ---
SET "PROJECT_ROOT=%~dp0"
SET "VENV_PATH=%PROJECT_ROOT%venv"

REM --- Check if the virtual environment exists ---
IF NOT EXIST "%VENV_PATH%\Scripts\activate.bat" (
    echo.
    echo [FATAL ERROR] Python virtual environment not found!
    echo Please run the setup steps first:
    echo 1. cd /d "%PROJECT_ROOT%"
    echo 2. python -m venv venv
    echo 3. venv\Scripts\activate
    echo 4. pip install mitmproxy flask sqlalchemy
    echo.
    pause
    exit /b
)

echo =================================================================
echo  A.R.G.U.S. System Starting (Production Mode)
echo  Activating Python environment...
echo =================================================================
echo.

REM --- Activate the virtual environment for this script ---
call "%VENV_PATH%\Scripts\activate.bat"

REM --- Start the Flask Web Dashboard in a new, activated window ---
echo [INFO] Starting Flask dashboard server... (http://127.0.0.1:5000)
start "A.R.G.U.S. Web UI" cmd /k "cd /d "%PROJECT_ROOT%" && python main.py"

REM --- Give the server a moment to start up ---
timeout /t 3 >nul

REM --- Start Mitmweb in this window (it inherits the activated venv) ---
echo [INFO] Starting Mitmweb real-time monitor... (http://127.0.0.1:8081)
mitmweb -s "%PROJECT_ROOT%proxy_addon.py" --web-port 8081 --listen-port 8080 --set block_global=false

endlocal
pause