@echo off
title Vigyan Pro Desktop
cd /d "%~dp0"

echo ========================================================
echo   Launching Vigyan Pro Sovereign Studio (Windows)
echo ========================================================

where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    python launch_desktop_win.py
    exit /b %ERRORLEVEL%
)

where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    py launch_desktop_win.py
    exit /b %ERRORLEVEL%
)

if exist "%~dp0..\.venv\Scripts\python.exe" (
    "%~dp0..\.venv\Scripts\python.exe" launch_desktop_win.py
    exit /b %ERRORLEVEL%
)

if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" launch_desktop_win.py
    exit /b %ERRORLEVEL%
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" launch_desktop_win.py
    exit /b %ERRORLEVEL%
)

if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" launch_desktop_win.py
    exit /b %ERRORLEVEL%
)

if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" launch_desktop_win.py
    exit /b %ERRORLEVEL%
)

REM Direct Edge App Mode fallback if Python is not in PATH
set "INDEX_PATH=%~dp0index.html"
set "FILE_URL=file:///%INDEX_PATH:\=/%"

start "" msedge.exe --app="%FILE_URL%" --window-size=1340,760 --force-dark-mode
exit /b 0
