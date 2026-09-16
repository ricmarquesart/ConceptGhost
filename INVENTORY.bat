@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo ConceptGhost - Stage 0 Machine Inventory
echo ============================================================
echo This command does not install Atlas, DA3, MoGe, or models.
echo It may hash existing model files, which can take time on large checkpoints.
echo Use --no-model-hashes to skip checkpoint hashing.
echo.

call :find_python
if errorlevel 1 exit /b 1
"%CG_PYTHON%" "%~dp0scripts\cg_bootstrap.py" inventory %*
exit /b %ERRORLEVEL%

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
exit /b 1
