@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo ConceptGhost - Safe Uninstall
echo ============================================================
echo Default mode is DRY RUN and preserves output files.
echo Use --apply to remove only files owned by ConceptGhost.
echo Modified and pre-existing files are preserved unless --force is explicit.
echo.

call :find_python
if errorlevel 1 exit /b 1
"%CG_PYTHON%" "%~dp0scripts\cg_bootstrap.py" uninstall %*
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
