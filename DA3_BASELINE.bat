@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "CG_EXIT=0"
set "CG_REPORT_ROOT=G:\My Drive\ConceptGhost"
call :init_timestamp

echo ============================================================
echo ConceptGhost - Stage 4 DA3 Baseline
echo ============================================================
echo Default mode is DRY RUN.
echo This stage DOES NOT replace existing Python packages, custom nodes,
echo workflows, or pre-existing DA3 checkouts.
echo It pins the public DA3 node pack only when ConceptGhost creates it.
echo Host bridge packages are installed only when the resolver proves they
echo are additions-only. DA3 runtime dependencies are built in a ConceptGhost-owned
echo isolated workspace, without rebuilding existing comfy-env environments.
echo.
echo IMPORTANT: close ComfyUI completely before running --apply.
echo To apply after reviewing the plan, run: DA3_BASELINE.bat --apply
echo Reports: %CG_REPORT_ROOT%
echo.

call :find_python
if errorlevel 1 (
  set "CG_EXIT=1"
  echo ERROR: Python was not found. > "%CG_TEMP_LOG%"
  type "%CG_TEMP_LOG%"
  goto :mirror_and_finish
)

"%CG_PYTHON%" "%~dp0scripts\cg_da3_baseline.py" %* > "%CG_TEMP_LOG%" 2>&1
set "CG_EXIT=%ERRORLEVEL%"
type "%CG_TEMP_LOG%"
goto :mirror_and_finish

:init_timestamp
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm-ss"') do set "CG_STAMP=%%I"
if not defined CG_STAMP set "CG_STAMP=unknown_time"
set "CG_TEMP_LOG=%TEMP%\ConceptGhost_DA3_BASELINE_%CG_STAMP%.log"
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
set "CG_REPORT_DIR=%CG_REPORT_ROOT%\Reports\DA3Baseline\%CG_STAMP%"
set "CG_COMPAT_DIR=%CG_REPORT_ROOT%\Tests\Compatibility\Stage4_%CG_STAMP%"
if exist "G:\My Drive" (
  if not exist "%CG_REPORT_DIR%" mkdir "%CG_REPORT_DIR%" >nul 2>nul
  if not exist "%CG_COMPAT_DIR%" mkdir "%CG_COMPAT_DIR%" >nul 2>nul
  if not exist "%CG_REPORT_ROOT%\Logs" mkdir "%CG_REPORT_ROOT%\Logs" >nul 2>nul
  if exist "%CG_TEMP_LOG%" copy /Y "%CG_TEMP_LOG%" "%CG_REPORT_ROOT%\Logs\DA3_BASELINE_%CG_STAMP%.log" >nul
  if exist "%CG_TEMP_LOG%" copy /Y "%CG_TEMP_LOG%" "%CG_REPORT_DIR%\command_output.log" >nul
  if exist "%CG_TEMP_LOG%" copy /Y "%CG_TEMP_LOG%" "%CG_COMPAT_DIR%\command_output.log" >nul
  for %%F in (
    stage4_plan.json
    da3_baseline_install.json
    stage4_pip_freeze_before.txt
    stage4_pip_freeze_after.txt
    stage4_environment_delta.json
    stage4_custom_nodes_before.json
    stage4_custom_nodes_after.json
    stage4_custom_nodes_delta.json
    stage4_comfy_env_before.json
    stage4_comfy_env_after.json
    stage4_comfy_env_delta.json
  ) do (
    if exist "C:\ConceptGhost\manifests\%%F" copy /Y "C:\ConceptGhost\manifests\%%F" "%CG_REPORT_DIR%\%%F" >nul
    if exist "C:\ConceptGhost\manifests\%%F" copy /Y "C:\ConceptGhost\manifests\%%F" "%CG_COMPAT_DIR%\%%F" >nul
  )
  if exist "C:\ConceptGhost\logs\da3_baseline_report.json" copy /Y "C:\ConceptGhost\logs\da3_baseline_report.json" "%CG_REPORT_DIR%\da3_baseline_report.json" >nul
  if exist "C:\ConceptGhost\logs\da3_baseline_report.json" copy /Y "C:\ConceptGhost\logs\da3_baseline_report.json" "%CG_COMPAT_DIR%\da3_baseline_report.json" >nul
) else (
  echo.
  echo WARNING: G:\My Drive is not mounted. Local report remains under C:\ConceptGhost.
)

if defined CG_PYTHON if exist "C:\ConceptGhost" (
  "%CG_PYTHON%" "%~dp0scripts\cg_storage.py" --reason "da3-baseline" >nul 2>&1
)

echo.
echo ============================================================
if "%CG_EXIT%"=="0" (
  echo DA3 baseline command finished.
  echo Drive reports: %CG_REPORT_DIR%
  echo Compatibility evidence: %CG_COMPAT_DIR%
  echo If this was DRY RUN and shows no blockers, run DA3_BASELINE.bat --apply.
) else (
  echo DA3 baseline command stopped with error code %CG_EXIT%.
  echo STOP: do not manually pip-install or update anything. Review the report first.
)
echo ============================================================
echo Press any key to close this window.
pause >nul
if exist "%CG_TEMP_LOG%" del /Q "%CG_TEMP_LOG%" >nul 2>nul
exit /b %CG_EXIT%
