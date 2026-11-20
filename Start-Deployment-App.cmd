@echo off
setlocal
title BuildSmart 360 Deployment Application
cd /d "%~dp0"

echo ====================================================================
echo   Starting BuildSmart 360 Standalone Deployment Application...
echo ====================================================================
echo.

:: Detect Python executable (check local venvs or system Python)
set "PYTHON_EXE=python"
if exist "..\BuildSmart_New\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=..\BuildSmart_New\.venv\Scripts\python.exe"
)

"%PYTHON_EXE%" run_deployer.py

if errorlevel 1 (
    echo.
    echo Startup failed. Press any key to exit.
    pause >nul
)
