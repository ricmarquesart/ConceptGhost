@echo off
setlocal
set "PY=%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [FAIL] ComfyUI Python not found: %PY%
  pause
  exit /b 1
)
"%PY%" "%~dp0Installer\resume_gate6.py"
set RC=%ERRORLEVEL%
if not "%RC%"=="0" echo [FAIL] Gate 6 resume/proof failed.
pause
exit /b %RC%
