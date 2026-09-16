@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "CG_EXIT=0"
set "CG_REPORT_ROOT=G:\My Drive\ConceptGhost"
call :init_timestamp

echo ============================================================
echo ConceptGhost - Stage 0/1 Safe Setup
echo ============================================================
echo This version DOES NOT install Atlas, DA3, MoGe, models, or modify PATH.
echo Default mode is DRY RUN. Use --apply to create C:\ConceptGhost.
echo Reports: %CG_REPORT_ROOT%
echo.

call :find_python
if errorlevel 1 (
  set "CG_EXIT=1"
  echo ERROR: Python was not found. > "%CG_TEMP_LOG%"
  type "%CG_TEMP_LOG%"
  goto :mirror_and_finish
)

"%CG_PYTHON%" "%~dp0scripts\cg_bootstrap.py" setup %* > "%CG_TEMP_LOG%" 2>&1
set "CG_EXIT=%ERRORLEVEL%"
type "%CG_TEMP_LOG%"

goto :mirror_and_finish

:init_timestamp
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm-ss"') do set "CG_STAMP=%%I"
if not defined CG_STAMP set "CG_STAMP=unknown_time"
set "CG_TEMP_LOG=%TEMP%\ConceptGhost_SETUP_%CG_STAMP%.log"
exit /b 0

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
exit /b 1

:mirror_and_finish
set "CG_REPORT_DIR=%CG_REPORT_ROOT%\Reports\Setup\%CG_STAMP%"
if exist "G:\My Drive" (
  if not exist "%CG_REPORT_DIR%" mkdir "%CG_REPORT_DIR%" >nul 2>nul
  if not exist "%CG_REPORT_ROOT%\Logs" mkdir "%CG_REPORT_ROOT%\Logs" >nul 2>nul
  if exist "%CG_TEMP_LOG%" copy /Y "%CG_TEMP_LOG%" "%CG_REPORT_ROOT%\Logs\SETUP_%CG_STAMP%.log" >nul
  if exist "%CG_TEMP_LOG%" copy /Y "%CG_TEMP_LOG%" "%CG_REPORT_DIR%\command_output.log" >nul
  for %%F in (setup_report.json install.log) do (
    if exist "C:\ConceptGhost\logs\%%F" copy /Y "C:\ConceptGhost\logs\%%F" "%CG_REPORT_DIR%\%%F" >nul
  )
  for %%F in (install_manifest.json disk_ledger.json disk_ledger.csv preinstall_inventory.json preinstall_disk.json preinstall_python_packages.txt) do (
    if exist "C:\ConceptGhost\manifests\%%F" copy /Y "C:\ConceptGhost\manifests\%%F" "%CG_REPORT_DIR%\%%F" >nul
  )
) else (
  echo.
  echo WARNING: G:\My Drive is not mounted. Local reports remain under C:\ConceptGhost.
)

echo.
echo ============================================================
if "%CG_EXIT%"=="0" (
  echo ConceptGhost setup finished.
  echo Drive reports: %CG_REPORT_DIR%
  echo Drive log:     %CG_REPORT_ROOT%\Logs\SETUP_%CG_STAMP%.log
  echo Review the result above before running SETUP.bat --apply.
) else (
  echo ConceptGhost setup stopped with error code %CG_EXIT%.
  echo Copy the error text above and send it back for diagnosis.
)
echo ============================================================
echo Press any key to close this window.
pause >nul
if exist "%CG_TEMP_LOG%" del /Q "%CG_TEMP_LOG%" >nul 2>nul
exit /b %CG_EXIT%
