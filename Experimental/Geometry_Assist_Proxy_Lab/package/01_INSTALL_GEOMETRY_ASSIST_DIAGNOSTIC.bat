@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Installer\install_geometry_assist.ps1"
set RC=%ERRORLEVEL%
echo.
if not "%RC%"=="0" echo INSTALL FAILED - see %%LOCALAPPDATA%%\ConceptGhost-GeometryAssistDiagnostic\Logs\install.log
pause
exit /b %RC%
