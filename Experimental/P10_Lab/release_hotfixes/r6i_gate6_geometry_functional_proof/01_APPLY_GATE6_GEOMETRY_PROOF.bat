@echo off
setlocal
set "PY=%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [FAIL] ComfyUI Python not found: %PY%
  pause
  exit /b 1
)
"%PY%" "%~dp0Installer\apply_hotfix.py"
set RC=%ERRORLEVEL%
if not "%RC%"=="0" echo [FAIL] R6I install failed.
pause
exit /b %RC%
