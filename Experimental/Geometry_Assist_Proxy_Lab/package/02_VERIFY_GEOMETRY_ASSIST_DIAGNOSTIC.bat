@echo off
setlocal
set "ROOT=%LOCALAPPDATA%\ConceptGhost-GeometryAssistDiagnostic"
if not exist "%ROOT%\Python\python.exe" (
  echo Runtime not installed: %ROOT%
  pause
  exit /b 2
)
"%ROOT%\Python\python.exe" "%ROOT%\Worker\geometry_assist_worker.py" --runtime-root "%ROOT%" --self-test
set RC=%ERRORLEVEL%
echo.
pause
exit /b %RC%
