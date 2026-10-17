@echo off
title Vigyan Pro Desktop
cd /d "%~dp0"

echo ========================================================
echo   Launching Vigyan Pro Sovereign Studio (Windows)
echo   100%% Offline Edge Intelligence • Shreyansh Singh
echo ========================================================

REM Check if Ollama is installed
where ollama >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo [!] Notice: Ollama is not detected on your Windows system.
    echo     Vigyan Pro runs 100%% locally using Ollama.
    echo     To install, download from: https://ollama.com/download/windows
    echo.
)

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

if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" launch_desktop_win.py
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

echo [WARN] Python not in PATH. Launching Microsoft Edge App Mode directly...
start "" msedge.exe --app="%FILE_URL%" --window-size=1340,760 --force-dark-mode
exit /b 0
