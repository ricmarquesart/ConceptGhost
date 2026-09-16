@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "CG_EXIT=0"
set "CG_REPORT_ROOT=G:\My Drive\ConceptGhost\Reports\StorageMigration"
set "CG_COMPAT_ROOT=G:\My Drive\ConceptGhost\Tests\Compatibility"
set "CG_LOG_ROOT=G:\My Drive\ConceptGhost\Logs"
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm-ss"') do set "CG_STAMP=%%I"
if not defined CG_STAMP set "CG_STAMP=unknown_time"
set "CG_REPORT_DIR=%CG_REPORT_ROOT%\Stage4S_Final_%CG_STAMP%"
set "CG_COMPAT_DIR=%CG_COMPAT_ROOT%\Stage4S_Final_%CG_STAMP%"
set "CG_TEMP_LOG=%TEMP%\ConceptGhost_STAGE4S_FINALIZE_%CG_STAMP%.log"

echo ============================================================
echo ConceptGhost - Stage 4S Final Evidence Gate
echo ============================================================
echo This gate is READ-ONLY with respect to C:\ConceptGhost.
echo It re-scans and verifies source/destination hashes.
echo It writes ONLY reports, logs, and an informational cleanup plan.
echo It does not move or modify the active DA3 runtime.
echo.
echo Durable project : G:\My Drive\ConceptGhost
echo Runtime contract : C:\ConceptGhostRuntime
echo Legacy runtime   : C:\ConceptGhost ^(grandfathered where required^)
echo Reports          : %CG_REPORT_DIR%
echo.

if not exist "G:\My Drive\ConceptGhost" (
  set "CG_EXIT=2"
  echo ERROR: Google Drive ConceptGhost root is not available.
  goto :finish
)

if not exist "%CG_REPORT_DIR%" mkdir "%CG_REPORT_DIR%" >nul 2>nul
if not exist "%CG_COMPAT_DIR%" mkdir "%CG_COMPAT_DIR%" >nul 2>nul
if not exist "%CG_LOG_ROOT%" mkdir "%CG_LOG_ROOT%" >nul 2>nul

call :find_python
if errorlevel 1 (
  set "CG_EXIT=1"
  echo ERROR: Python was not found by the protected ConceptGhost locator. > "%CG_TEMP_LOG%"
  type "%CG_TEMP_LOG%"
  goto :mirror_and_finish
)
echo Python           : %CG_PYTHON%
"%CG_PYTHON%" "%~dp0scripts\cg_stage4s_finalize.py" --config "%~dp0config.yml" --legacy-root "C:\ConceptGhost" --evidence-dir "%CG_REPORT_DIR%" > "%CG_TEMP_LOG%" 2>&1
set "CG_EXIT=%ERRORLEVEL%"
type "%CG_TEMP_LOG%"

:mirror_and_finish
if exist "%CG_TEMP_LOG%" copy /Y "%CG_TEMP_LOG%" "%CG_REPORT_DIR%\command_output.log" >nul 2>nul
if exist "%CG_TEMP_LOG%" copy /Y "%CG_TEMP_LOG%" "%CG_COMPAT_DIR%\command_output.log" >nul 2>nul
if exist "%CG_TEMP_LOG%" copy /Y "%CG_TEMP_LOG%" "%CG_LOG_ROOT%\STAGE4S_FINALIZE_%CG_STAMP%.log" >nul 2>nul
if exist "%CG_REPORT_DIR%\stage4s_cutover_report.json" copy /Y "%CG_REPORT_DIR%\stage4s_cutover_report.json" "%CG_COMPAT_DIR%\stage4s_cutover_report.json" >nul 2>nul
if exist "%CG_REPORT_DIR%\stage4s_cleanup_plan.json" copy /Y "%CG_REPORT_DIR%\stage4s_cleanup_plan.json" "%CG_COMPAT_DIR%\stage4s_cleanup_plan.json" >nul 2>nul

:finish
echo.
echo ============================================================
if "%CG_EXIT%"=="0" (
  echo Stage 4S final evidence gate finished successfully.
  echo Review: %CG_REPORT_DIR%
  echo No legacy source file was changed by this gate.
) else (
  echo Stage 4S final evidence gate stopped with error code %CG_EXIT%.
  echo Review: %CG_REPORT_DIR%
  echo STOP: do not clean legacy C:\ConceptGhost data.
)
echo ============================================================
echo Press any key to close this window.
pause >nul
exit /b %CG_EXIT%

:find_python
set "CG_PYTHON="
if not exist "%~dp0scripts\cg_find_python.ps1" exit /b 1
for /f "usebackq delims=" %%P in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\cg_find_python.ps1" -ProjectRoot "G:\My Drive\ConceptGhost" -LegacyRoot "C:\ConceptGhost"`) do (
  if not defined CG_PYTHON set "CG_PYTHON=%%P"
)
if defined CG_PYTHON if exist "%CG_PYTHON%" exit /b 0
set "CG_PYTHON="
exit /b 1
