@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "CG_EXIT=0"
set "CG_REPORT_ROOT=G:\My Drive\ConceptGhost"
call :init_timestamp

echo ============================================================
echo ConceptGhost - Safe Uninstall
echo ============================================================
echo Default mode is DRY RUN and preserves output files.
echo Use --apply to remove only files owned by ConceptGhost.
echo Modified and pre-existing files are preserved unless --force is explicit.
echo Reports: %CG_REPORT_ROOT%
echo.

call :find_python
if errorlevel 1 (
  set "CG_EXIT=1"
  echo ERROR: Python was not found. > "%CG_TEMP_LOG%"
  type "%CG_TEMP_LOG%"
  goto :mirror_and_finish
)

"%CG_PYTHON%" "%~dp0scripts\cg_bootstrap.py" uninstall %* > "%CG_TEMP_LOG%" 2>&1
set "CG_EXIT=%ERRORLEVEL%"
type "%CG_TEMP_LOG%"

goto :mirror_and_finish

:init_timestamp
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm-ss"') do set "CG_STAMP=%%I"
if not defined CG_STAMP set "CG_STAMP=unknown_time"
set "CG_TEMP_LOG=%TEMP%\ConceptGhost_UNINSTALL_%CG_STAMP%.log"
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
set "CG_REPORT_DIR=%CG_REPORT_ROOT%\Reports\Uninstall\%CG_STAMP%"
if exist "G:\My Drive" (
  if not exist "%CG_REPORT_DIR%" mkdir "%CG_REPORT_DIR%" >nul 2>nul
  if not exist "%CG_REPORT_ROOT%\Logs" mkdir "%CG_REPORT_ROOT%\Logs" >nul 2>nul
  if exist "%CG_TEMP_LOG%" copy /Y "%CG_TEMP_LOG%" "%CG_REPORT_ROOT%\Logs\UNINSTALL_%CG_STAMP%.log" >nul
  if exist "%CG_TEMP_LOG%" copy /Y "%CG_TEMP_LOG%" "%CG_REPORT_DIR%\command_output.log" >nul
  if exist "C:\ConceptGhost\logs\uninstall_report.json" copy /Y "C:\ConceptGhost\logs\uninstall_report.json" "%CG_REPORT_DIR%\uninstall_report.json" >nul
) else (
  echo.
  echo WARNING: G:\My Drive is not mounted. Local reports remain under C:\ConceptGhost.
)

if defined CG_PYTHON if exist "C:\ConceptGhost" (
  "%CG_PYTHON%" "%~dp0scripts\cg_storage.py" --reason "uninstall" >nul 2>&1
)

echo.
echo ============================================================
if "%CG_EXIT%"=="0" (
  echo ConceptGhost uninstall command finished.
  echo Drive reports: %CG_REPORT_DIR%
  echo Drive log:     %CG_REPORT_ROOT%\Logs\UNINSTALL_%CG_STAMP%.log
  echo Storage TXT:   %CG_REPORT_ROOT%\Storage\ConceptGhost_Disk_Usage.txt
) else (
  echo ConceptGhost uninstall stopped with error code %CG_EXIT%.
)
echo ============================================================
echo Press any key to close this window.
pause >nul
if exist "%CG_TEMP_LOG%" del /Q "%CG_TEMP_LOG%" >nul 2>nul
exit /b %CG_EXIT%
