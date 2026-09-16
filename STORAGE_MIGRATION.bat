@echo off
setlocal EnableExtensions
cd /d "%~dp0"

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm-ss"') do set "CG_STAMP=%%I"
if not defined CG_STAMP set "CG_STAMP=unknown_time"

set "CG_DRIVE_ROOT=G:\My Drive\ConceptGhost"
set "CG_REPORT_DIR=%CG_DRIVE_ROOT%\Reports\StorageMigration\%CG_STAMP%"
set "CG_COMPAT_DIR=%CG_DRIVE_ROOT%\Tests\Compatibility\Stage4S_%CG_STAMP%"
set "CG_LOG=%CG_DRIVE_ROOT%\Logs\STORAGE_MIGRATION_%CG_STAMP%.log"
set "CG_REPORT_JSON=%CG_REPORT_DIR%\stage4s_storage_migration.json"
set "CG_MODE=DRY RUN"

echo %* | findstr /I /C:"--copy" >nul && set "CG_MODE=COPY"
echo %* | findstr /I /C:"--cutover-check" >nul && set "CG_MODE=CUTOVER CHECK"

echo ============================================================
echo ConceptGhost - Stage 4S Storage Layout Migration
echo ============================================================
echo Mode: %CG_MODE%
echo Default mode is DRY RUN.
echo --copy copies PROJECT files with SHA-256 verification and preserves C: sources.
echo --cutover-check only verifies G: readiness and preserves C: sources.
echo No cleanup action is exposed by this launcher.
echo Reports: %CG_REPORT_DIR%
echo.

if not exist "G:\My Drive" (
  echo ERROR: G:\My Drive is not mounted.
  echo Press any key to close this window.
  pause >nul
  exit /b 2
)

if not exist "%CG_REPORT_DIR%" mkdir "%CG_REPORT_DIR%" >nul 2>nul
if not exist "%CG_COMPAT_DIR%" mkdir "%CG_COMPAT_DIR%" >nul 2>nul
if not exist "%CG_DRIVE_ROOT%\Logs" mkdir "%CG_DRIVE_ROOT%\Logs" >nul 2>nul

set "CG_PYTHON="
where python.exe >nul 2>nul && set "CG_PYTHON=python.exe"
if not defined CG_PYTHON where py.exe >nul 2>nul && set "CG_PYTHON=py.exe"
if not defined CG_PYTHON (
  echo ERROR: Python was not found.
  echo Press any key to close this window.
  pause >nul
  exit /b 2
)

"%CG_PYTHON%" "%~dp0scripts\cg_storage_migration.py" --report-json "%CG_REPORT_JSON%" %* > "%CG_LOG%" 2>&1
set "CG_EXIT=%ERRORLEVEL%"
type "%CG_LOG%"

copy /Y "%CG_LOG%" "%CG_REPORT_DIR%\command_output.log" >nul 2>nul
copy /Y "%CG_LOG%" "%CG_COMPAT_DIR%\command_output.log" >nul 2>nul
if exist "%CG_REPORT_JSON%" copy /Y "%CG_REPORT_JSON%" "%CG_COMPAT_DIR%\stage4s_storage_migration.json" >nul 2>nul

echo.
echo ============================================================
if "%CG_EXIT%"=="0" (
  echo Stage 4S command completed.
  echo Evidence: %CG_REPORT_DIR%
  echo Compatibility evidence: %CG_COMPAT_DIR%
) else (
  echo Stage 4S stopped with error code %CG_EXIT%.
  echo Review the report before proceeding.
)
echo ============================================================
echo Press any key to close this window.
pause >nul
exit /b %CG_EXIT%
