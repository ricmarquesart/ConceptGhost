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
"%PY%" "%~dp0resume_gate7.py" --comfy-root "%COMFYROOT%"
if errorlevel 1 (
  echo [FAIL] Gate 7 resume failed. Keep this console output and RUN_AUDIT_BUNDLE.zip.
  pause
  exit /b 1
)
echo [PASS] Gate 7 resume completed.
pause
