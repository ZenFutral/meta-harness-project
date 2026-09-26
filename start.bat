@echo off
setlocal enabledelayedexpansion
title Meta-Harness // 1-Click System Launcher

echo.
echo ==================================================================
echo   Meta-Harness // SWE Multi-Agent Ecosystem 1-Click Launcher
echo ==================================================================
echo.

cd /d "%~dp0"

:: Check for Python in PATH
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PY_CMD=python"
    goto :RUN
)

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PY_CMD=py"
    goto :RUN
)

echo [!] Error: Python was not found in your system PATH.
echo [!] Please install Python 3.9+ from https://www.python.org/
echo.
pause
exit /b 1

:RUN
echo [*] Launching Meta-Harness functions, web server, and dashboard...
echo.
"%PY_CMD%" "%~dp0start.py" %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo [!] Meta-Harness exited with error code %ERRORLEVEL%.
    pause
)
