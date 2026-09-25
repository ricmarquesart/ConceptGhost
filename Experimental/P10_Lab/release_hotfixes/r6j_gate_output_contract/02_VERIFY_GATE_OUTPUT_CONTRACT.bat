@echo off
setlocal
cd /d "%~dp0"
set "COMFYROOT=%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI"
set "PY=%COMFYROOT%\.venv\Scripts\python.exe"
"%PY%" "%~dp0Installer\verify_hotfix.py" --comfy-root "%COMFYROOT%"
if errorlevel 1 (
  echo [FAIL] R6J verification failed.
  pause
  exit /b 1
)
echo [PASS] R6J verified.
pause
