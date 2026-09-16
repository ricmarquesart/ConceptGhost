@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "CG_EXIT=0"

echo ============================================================
echo ConceptGhost - Stage 4S Storage Tracker
echo ============================================================
echo Durable project root : G:\My Drive\ConceptGhost
echo New runtime root      : C:\ConceptGhostRuntime
echo Legacy DA3 runtime    : C:\ConceptGhost\cache ^(grandfathered; read-only accounting^)
echo Drive TXT             : G:\My Drive\ConceptGhost\Storage\ConceptGhost_Disk_Usage.txt
echo.

call :find_python
if errorlevel 1 (
  set "CG_EXIT=1"
  echo ERROR: Python was not found.
  goto :finish
)

"%CG_PYTHON%" "%~dp0scripts\cg_storage.py" --config "%~dp0config.yml" --legacy-root "C:\ConceptGhost" --reason "manual" %*
set "CG_EXIT=%ERRORLEVEL%"

:finish
echo.
echo ============================================================
if "%CG_EXIT%"=="0" (
  echo Storage tracker updated.
  echo G:\My Drive\ConceptGhost\Storage\ConceptGhost_Disk_Usage.txt
) else (
  echo Storage tracker stopped with error code %CG_EXIT%.
)
echo ============================================================
echo Press any key to close this window.
pause >nul
exit /b %CG_EXIT%

:find_python
set "CG_PYTHON="
for %%P in (py.exe python.exe) do (
  if not defined CG_PYTHON where %%P >nul 2>nul ^&^& set "CG_PYTHON=%%P"
)
if defined CG_PYTHON exit /b 0
if exist "G:\My Drive\ConceptGhost\Manifests\preinstall_inventory.json" (
  for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "$j=Get-Content 'G:\My Drive\ConceptGhost\Manifests\preinstall_inventory.json' -Raw ^| ConvertFrom-Json; $j.comfyui.selected.python_executable"`) do set "CG_PYTHON=%%P"
)
if defined CG_PYTHON if exist "%CG_PYTHON%" exit /b 0
if exist "C:\ConceptGhost\manifests\preinstall_inventory.json" (
  for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "$j=Get-Content 'C:\ConceptGhost\manifests\preinstall_inventory.json' -Raw ^| ConvertFrom-Json; $j.comfyui.selected.python_executable"`) do set "CG_PYTHON=%%P"
)
if defined CG_PYTHON if exist "%CG_PYTHON%" exit /b 0
exit /b 1
