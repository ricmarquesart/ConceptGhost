@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "CG_EXIT=0"
set "CG_REPORT_ROOT=G:\My Drive\ConceptGhost"
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm-ss"') do set "CG_STAMP=%%I"
if not defined CG_STAMP set "CG_STAMP=unknown_time"
set "CG_TEMP_LOG=%TEMP%\ConceptGhost_TEST_%CG_STAMP%.log"
set "CG_REPORT_DIR=%CG_REPORT_ROOT%\Tests\Local\%CG_STAMP%"

echo ============================================================
echo ConceptGhost - Local Test Suite
echo ============================================================
echo Test output: %CG_REPORT_DIR%
echo.

set "CG_PYTHON="
for %%P in (py.exe python.exe) do (
  if not defined CG_PYTHON where %%P >nul 2>nul && set "CG_PYTHON=%%P"
)
if not defined CG_PYTHON (
  echo ERROR: Python was not found. > "%CG_TEMP_LOG%"
  set "CG_EXIT=1"
) else (
  "%CG_PYTHON%" -m unittest discover -s tests -v > "%CG_TEMP_LOG%" 2>&1
  set "CG_EXIT=%ERRORLEVEL%"
)

type "%CG_TEMP_LOG%"
if exist "G:\My Drive" (
  if not exist "%CG_REPORT_DIR%" mkdir "%CG_REPORT_DIR%" >nul 2>nul
  copy /Y "%CG_TEMP_LOG%" "%CG_REPORT_DIR%\test_output.log" >nul
  copy /Y "%CG_TEMP_LOG%" "%CG_REPORT_ROOT%\Logs\TEST_%CG_STAMP%.log" >nul 2>nul
) else (
  echo.
  echo WARNING: G:\My Drive is not mounted. Test log was not mirrored to Drive.
)

if defined CG_PYTHON if exist "C:\ConceptGhost" (
  "%CG_PYTHON%" "%~dp0scripts\cg_storage.py" --reason "test" >nul 2>&1
)

echo.
echo ============================================================
if "%CG_EXIT%"=="0" (
  echo ConceptGhost tests passed.
) else (
  echo ConceptGhost tests failed with error code %CG_EXIT%.
)
echo Drive test report: %CG_REPORT_DIR%\test_output.log
echo ============================================================
echo Press any key to close this window.
pause >nul
if exist "%CG_TEMP_LOG%" del /Q "%CG_TEMP_LOG%" >nul 2>nul
exit /b %CG_EXIT%
