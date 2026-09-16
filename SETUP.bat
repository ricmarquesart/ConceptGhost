@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "CG_EXIT=0"

echo ============================================================
echo ConceptGhost - Stage 0/1 Safe Setup
echo ============================================================
echo This version DOES NOT install Atlas, DA3, MoGe, models, or modify PATH.
echo Default mode is DRY RUN. Use --apply to create C:\ConceptGhost.
echo.

call :find_python
if errorlevel 1 (
  set "CG_EXIT=1"
  goto :finish
)

"%CG_PYTHON%" "%~dp0scripts\cg_bootstrap.py" setup %*
set "CG_EXIT=%ERRORLEVEL%"
if not "%CG_EXIT%"=="0" (
  echo.
  echo Setup returned error code %CG_EXIT%.
)
goto :finish

:find_python
set "CG_PYTHON="
for %%P in (py.exe python.exe) do (
  if not defined CG_PYTHON (
    where %%P >nul 2>nul && set "CG_PYTHON=%%P"
  )
)
if defined CG_PYTHON exit /b 0

for %%P in (
  "C:\ComfyUI_windows_portable\python_embeded\python.exe"
  "C:\ComfyUI\venv\Scripts\python.exe"
  "D:\ComfyUI_windows_portable\python_embeded\python.exe"
  "D:\ComfyUI\venv\Scripts\python.exe"
) do (
  if not defined CG_PYTHON if exist %%~P set "CG_PYTHON=%%~P"
)
if defined CG_PYTHON exit /b 0

echo ERROR: Python was not found.
echo Run this BAT from a machine with Python or use --comfyui-root with INVENTORY.bat.
exit /b 1

:finish
echo.
echo ============================================================
if "%CG_EXIT%"=="0" (
  echo ConceptGhost setup finished.
  echo Review the result above before running SETUP.bat --apply.
) else (
  echo ConceptGhost setup stopped with error code %CG_EXIT%.
  echo Copy the error text above and send it back for diagnosis.
)
echo ============================================================
echo Press any key to close this window.
pause >nul
exit /b %CG_EXIT%
