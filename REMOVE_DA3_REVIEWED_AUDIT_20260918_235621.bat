@echo off
setlocal
cd /d "%~dp0"
echo.
echo ============================================================
echo  ConceptGhost - Reviewed DA3 Cleanup v0.32.2
echo ============================================================
echo  Deletes ONLY the two DA3-exclusive paths approved in the
echo  reviewed 20260918_235621 audit.
echo.
set "PS1=%~dp0remove_da3_reviewed_audit_20260918_235621.ps1"
if not exist "%PS1%" set "PS1=%~dp0Scripts\remove_da3_reviewed_audit_20260918_235621.ps1"
if not exist "%PS1%" (
  echo [FAIL] PowerShell cleanup script was not found.
  echo No files were changed.
  pause
  exit /b 1
)
echo [INFO] Using script:
echo   %PS1%
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
if errorlevel 1 (
  echo.
  echo [FAIL] Cleanup was blocked or failed. Review the message above.
  echo No broader cleanup is attempted.
  pause
  exit /b 1
)
pause
