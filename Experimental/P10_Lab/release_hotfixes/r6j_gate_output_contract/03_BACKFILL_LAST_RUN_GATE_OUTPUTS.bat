@echo off
setlocal
cd /d "%~dp0"
set "COMFYROOT=%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI"
set "PY=%COMFYROOT%\.venv\Scripts\python.exe"
"%PY%" "%~dp0Installer\backfill_last_attempt.py" --comfy-root "%COMFYROOT%"
if errorlevel 1 (
  echo [FAIL] Gate output backfill failed. Keep this console output.
  pause
  exit /b 1
)
echo [PASS] Gate output folders created beside the P9 run.
pause
