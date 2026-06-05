@echo off
REM ============================================================================
REM PDB Clone - Quick Start Script
REM ============================================================================

echo.
echo ========================================================================
echo                    PDB CLONE - Quick Start
echo ========================================================================
echo.
echo 1. Start Development Server
echo 2. Create Superuser
echo 3. Open PowerShell Startup Menu
echo 4. Exit
echo.

set /p choice="Select an option (1-4): "

if "%choice%"=="1" (
    echo.
    echo Starting Django Development Server...
    echo.
    echo Server URL: http://127.0.0.1:8000/
    echo Admin Panel: http://127.0.0.1:8000/admin/
    echo.
    echo Press Ctrl+C to stop the server
    echo.
    .venv\Scripts\python.exe manage.py runserver
)

if "%choice%"=="2" (
    echo.
    echo Creating Superuser...
    echo.
    .venv\Scripts\python.exe manage.py createsuperuser
    echo.
    pause
)

if "%choice%"=="3" (
    echo.
    echo Opening PowerShell Startup Menu...
    echo.
    powershell -ExecutionPolicy Bypass -File start.ps1
)

if "%choice%"=="4" (
    echo.
    echo Goodbye!
    echo.
    exit
)

echo.
pause
