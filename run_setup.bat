@echo off
title Cogito Requiem Launcher
color 0A

echo ==================================================
echo       COGITO REQUIEM - AUTO SETUP ^& LAUNCH
echo ==================================================
echo.

:: ============================================
:: STEP 0: Check if Python is installed
:: ============================================
echo [0/4] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
echo       Python found!
echo.

:: ============================================
:: STEP 1: Check and Install Requirements
:: ============================================
echo [1/4] Checking dependencies...

:: Quick check - see if crewai and fastapi are installed
python -c "import crewai; import fastapi; import uvicorn" >nul 2>&1
if %errorlevel% neq 0 (
    echo       Missing packages detected. Installing...
    echo       This may take 2-5 minutes on first run...
    echo.
    
    :: Check if requirements.txt exists
    if not exist "requirements.txt" (
        color 0C
        echo ERROR: requirements.txt not found!
        echo Please make sure requirements.txt is in the same folder.
        pause
        exit /b 1
    )
    
    :: Install with optimizations for speed
    pip install -r requirements.txt --prefer-binary --quiet
    
    if %errorlevel% neq 0 (
        color 0C
        echo.
        echo ERROR: Failed to install dependencies!
        echo Try running manually: pip install -r requirements.txt
        pause
        exit /b 1
    )
    
    echo       Dependencies installed successfully!
) else (
    echo       All dependencies already installed!
)
echo.

:: ============================================
:: STEP 2: Start the Backend API
:: ============================================
echo [2/4] Launching Python Backend (api.py)...

:: Check if api.py exists
if not exist "api.py" (
    color 0C
    echo ERROR: api.py not found!
    pause
    exit /b 1
)

start "Cogito Backend API" cmd /k "title Cogito Backend API - DO NOT CLOSE && color 0B && python api.py"

:: ============================================
:: STEP 3: Start the Frontend Web Server
:: ============================================
echo [3/4] Launching Web Server (port 5500)...
start "Cogito Frontend Server" cmd /k "title Cogito Frontend - DO NOT CLOSE && color 0E && python -m http.server 5500"

:: ============================================
:: STEP 4: Wait and Open Browser
:: ============================================
echo.
echo Waiting for servers to initialize...
timeout /t 4 /nobreak >nul

echo [4/4] Opening Browser...
start http://localhost:5500

:: ============================================
:: DONE
:: ============================================
echo.
color 0A
echo ==================================================
echo   COGITO REQUIEM IS RUNNING!
echo ==================================================
echo.
echo   Frontend: http://localhost:5500
echo   Backend:  http://localhost:8000
echo.
echo   DO NOT close the terminal windows that opened.
echo   You can minimize them.
echo.
echo   To STOP the system, close both terminal windows
echo   or press Ctrl+C in each one.
echo ==================================================
echo.
pause