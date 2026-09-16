@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "CG_EXIT=0"
set "CG_REPORT_ROOT=G:\My Drive\ConceptGhost"
call :init_timestamp

echo ============================================================
echo ConceptGhost - Stage 2 Atlas Camera Core
echo ============================================================
echo Default mode is DRY RUN.
echo This stage installs ONLY the Atlas Camera Git repository.
echo It does NOT install GeoCalib, OpenCV, Kornia, DA3, MoGe packages or models.
echo To apply after reviewing the plan, run: ATLAS_CORE.bat --apply
echo Reports: %CG_REPORT_ROOT%
echo.

call :find_python
if errorlevel 1 (
  set "CG_EXIT=1"
  echo ERROR: Python was not found. > "%CG_TEMP_LOG%"
  type "%CG_TEMP_LOG%"
  goto :mirror_and_finish
)

"%CG_PYTHON%" "%~dp0scripts\cg_atlas_core.py" %* > "%CG_TEMP_LOG%" 2>&1
set "CG_EXIT=%ERRORLEVEL%"
type "%CG_TEMP_LOG%"
goto :mirror_and_finish

:init_timestamp
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm-ss"') do set "CG_STAMP=%%I"
if not defined CG_STAMP set "CG_STAMP=unknown_time"
set "CG_TEMP_LOG=%TEMP%\ConceptGhost_ATLAS_CORE_%CG_STAMP%.log"
exit /b 0

:find_python
set "CG_PYTHON="
for %%P in (py.exe python.exe) do (
  if not defined CG_PYTHON (
    where %%P >nul 2>nul && set "CG_PYTHON=%%P"
  )
)
if defined CG_PYTHON exit /b 0
if exist "C:\ConceptGhost\manifests\preinstall_inventory.json" (
  for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "$j=Get-Content 'C:\ConceptGhost\manifests\preinstall_inventory.json' -Raw ^| ConvertFrom-Json; $j.comfyui.selected.python_executable"`) do set "CG_PYTHON=%%P"
)
if defined CG_PYTHON if exist "%CG_PYTHON%" exit /b 0
exit /b 1

:mirror_and_finish
set "CG_REPORT_DIR=%CG_REPORT_ROOT%\Reports\AtlasCore\%CG_STAMP%"
if exist "G:\My Drive" (
  if not exist "%CG_REPORT_DIR%" mkdir "%CG_REPORT_DIR%" >nul 2>nul
  if not exist "%CG_REPORT_ROOT%\Logs" mkdir "%CG_REPORT_ROOT%\Logs" >nul 2>nul
  if exist "%CG_TEMP_LOG%" copy /Y "%CG_TEMP_LOG%" "%CG_REPORT_ROOT%\Logs\ATLAS_CORE_%CG_STAMP%.log" >nul
  if exist "%CG_TEMP_LOG%" copy /Y "%CG_TEMP_LOG%" "%CG_REPORT_DIR%\command_output.log" >nul
  for %%F in (atlas_core_install.json) do (
    if exist "C:\ConceptGhost\manifests\%%F" copy /Y "C:\ConceptGhost\manifests\%%F" "%CG_REPORT_DIR%\%%F" >nul
  )
  for %%F in (atlas_core_report.json) do (
    if exist "C:\ConceptGhost\logs\%%F" copy /Y "C:\ConceptGhost\logs\%%F" "%CG_REPORT_DIR%\%%F" >nul
  )
) else (
  echo.
  echo WARNING: G:\My Drive is not mounted. Local report remains under C:\ConceptGhost.
)

if defined CG_PYTHON if exist "C:\ConceptGhost" (
  "%CG_PYTHON%" "%~dp0scripts\cg_storage.py" --reason "atlas-core" >nul 2>&1
)

echo.
echo ============================================================
if "%CG_EXIT%"=="0" (
  echo Atlas Core command finished.
  echo Drive reports: %CG_REPORT_DIR%
  echo If this was DRY RUN and looks correct, run ATLAS_CORE.bat --apply.
) else (
  echo Atlas Core command stopped with error code %CG_EXIT%.
)
echo ============================================================
echo Press any key to close this window.
pause >nul
if exist "%CG_TEMP_LOG%" del /Q "%CG_TEMP_LOG%" >nul 2>nul
exit /b %CG_EXIT%
