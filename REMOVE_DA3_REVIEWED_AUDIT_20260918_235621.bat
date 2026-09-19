@echo off
setlocal
cd /d "%~dp0"
echo.
echo ============================================================
echo  ConceptGhost - Reviewed DA3 Cleanup v0.32
echo ============================================================
echo  This cleanup is pinned to the reviewed 20260918_235621 audit.
echo  It can remove ONLY:
echo    C:\ConceptGhost\cache\da3-comfy-env
echo    C:\ConceptGhost\config\da3_host_paths.json
echo.
echo  It will NOT remove Pixi, DA3 plugin/models, Python, Torch,
echo  CUDA, NumPy, Single View, Multi View/Trellis, or other workflows.
echo.

set "PS1=%~dp0remove_da3_reviewed_audit_20260918_235621.ps1"
if not exist "%PS1%" set "PS1=%~dp0Scripts\remove_da3_reviewed_audit_20260918_235621.ps1"

if not exist "%PS1%" (
  echo [FAIL] PowerShell cleanup script was not found.
  echo Expected either:
  echo   %~dp0remove_da3_reviewed_audit_20260918_235621.ps1
  echo or:
  echo   %~dp0Scripts\remove_da3_reviewed_audit_20260918_235621.ps1
  echo.
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
