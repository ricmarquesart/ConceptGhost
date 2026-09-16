@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

set "PROJECT_ROOT=%CD%"
set "LOCK=%PROJECT_ROOT%\references\SOURCE_LOCK.json"
set "CG_REPORT_DIR=G:\My Drive\ConceptGhost\References\Audit_and_Videos\Reference_Verification"

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm-ss"') do set "CG_STAMP=%%I"
if not defined CG_STAMP set "CG_STAMP=unknown_time"

set "REPORT_TXT=%CG_REPORT_DIR%\reference_verification_%CG_STAMP%.txt"
set "REPORT_JSON=%CG_REPORT_DIR%\reference_verification_%CG_STAMP%.json"

echo ============================================================
echo ConceptGhost - Reference Code Verification
echo ============================================================
echo Read-only verification of pinned reference mirrors.
echo Source lock: %LOCK%
echo Reports: %CG_REPORT_DIR%
echo.

if not exist "%LOCK%" (
  echo ERROR: source lock not found.
  echo Press any key to close.
  pause >nul
  exit /b 2
)

if not exist "G:\My Drive" (
  echo ERROR: G:\My Drive is not mounted.
  echo Press any key to close.
  pause >nul
  exit /b 2
)

if not exist "%CG_REPORT_DIR%" mkdir "%CG_REPORT_DIR%" >nul 2>nul

set "CG_PYTHON="
for %%P in (py.exe python.exe) do (
  if not defined CG_PYTHON where %%P >nul 2>nul && set "CG_PYTHON=%%P"
)
if not defined CG_PYTHON (
  echo ERROR: Python was not found on PATH.
  echo Press any key to close.
  pause >nul
  exit /b 2
)

"%CG_PYTHON%" "%PROJECT_ROOT%\scripts\cg_verify_references.py" --lock "%LOCK%" --report-txt "%REPORT_TXT%" --report-json "%REPORT_JSON%"
set "CG_EXIT=%ERRORLEVEL%"

echo.
echo ============================================================
if "%CG_EXIT%"=="0" (
  echo Reference verification PASSED.
) else (
  echo Reference verification found missing or mismatched sources.
)
echo TXT: %REPORT_TXT%
echo JSON: %REPORT_JSON%
echo ============================================================
echo Press any key to close.
pause >nul
exit /b %CG_EXIT%
