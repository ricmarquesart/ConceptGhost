@echo off
setlocal
set "ROOT=%LOCALAPPDATA%\ConceptGhost-GeometryAssistDiagnostic"
echo This removes ONLY the isolated Geometry Assist Diagnostic runtime:
echo %ROOT%
echo.
choice /M "Continue"
if errorlevel 2 exit /b 0
if exist "%ROOT%" rmdir /S /Q "%ROOT%"
echo Removed. Official ConceptGhost/ComfyUI/MoGe/Lotus files were not targeted.
pause
