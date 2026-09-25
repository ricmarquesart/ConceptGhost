@echo off
setlocal
cd /d "%~dp0"
set "COMFYROOT=%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI"
set "PY=%COMFYROOT%\.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [FAIL] ComfyUI Python not found: %PY%
  pause
  exit /b 1
)
"%PY%" "%~dp0Installer\apply_hotfix.py" --comfy-root "%COMFYROOT%"
if errorlevel 1 (
  echo [FAIL] R6J install failed.
  pause
  exit /b 1
)
echo [PASS] R6J installed.
pause
