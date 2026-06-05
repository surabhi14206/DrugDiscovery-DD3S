@echo off
REM Install Python packages and automatically unblock DLLs/PYDs
REM Usage: install_and_unblock.bat package-name
REM Example: install_and_unblock.bat rdkit

echo Installing packages: %*
pip install %*

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Unblocking DLL and PYD files...
    powershell -Command "Get-ChildItem -Path '.venv\Lib\site-packages' -Recurse -Include *.dll,*.pyd | Unblock-File -ErrorAction SilentlyContinue"
    echo.
    echo [SUCCESS] All files unblocked!
    echo Your packages are ready to use.
) else (
    echo.
    echo [ERROR] Installation failed. Files not unblocked.
)

pause
