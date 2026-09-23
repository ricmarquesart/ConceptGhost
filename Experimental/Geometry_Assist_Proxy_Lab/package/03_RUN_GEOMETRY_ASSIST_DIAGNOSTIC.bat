@echo off
setlocal
set "ROOT=%LOCALAPPDATA%\ConceptGhost-GeometryAssistDiagnostic"
if not exist "%ROOT%\Python\python.exe" (
  echo Runtime not installed. Run 01_INSTALL_GEOMETRY_ASSIST_DIAGNOSTIC.bat first.
  pause
  exit /b 2
)
set "INPUT=%~1"
if "%INPUT%"=="" (
  set /p "INPUT=Paste the full path to the source PNG/JPG: "
)
if "%INPUT%"=="" exit /b 2
"%ROOT%\Python\python.exe" "%ROOT%\Worker\geometry_assist_worker.py" --runtime-root "%ROOT%" --input "%INPUT%"
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" (
  echo PASS. Open outputs with 04_OPEN_GEOMETRY_ASSIST_OUTPUTS.bat
) else (
  echo RUN FAILED. Check %ROOT%\Logs and the newest Outputs run folder.
)
pause
exit /b %RC%
