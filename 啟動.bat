@echo off
title TaiwanStockPicker

echo ================================================
echo   Taiwan Stock Picker - Starting...
echo ================================================
echo.

cd /d "%~dp0"

python --version > nul 2>&1
if not errorlevel 1 (
    set PYTHON=python
    goto :install
)
py --version > nul 2>&1
if not errorlevel 1 (
    set PYTHON=py
    goto :install
)

echo [ERROR] Python not found!
echo Please install Python 3.9+ from https://www.python.org/downloads/
echo Make sure to check "Add Python to PATH" during installation.
pause
exit /b 1

:install
echo [1/2] Installing required packages...
echo       First run may take 1-2 minutes, please wait...
echo.
%PYTHON% -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] Package installation failed. Check your internet connection.
    pause
    exit /b 1
)
echo [OK] Packages ready.
echo.

:run
echo [2/2] Starting web interface...
echo       Browser will open automatically...
echo.
echo ================================================
echo   Close this window to stop the program
echo ================================================
echo.
%PYTHON% -m streamlit run app.py --server.headless false --browser.gatherUsageStats false

echo.
echo Program stopped.
pause
