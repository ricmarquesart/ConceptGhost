@echo off
set "OUT=%LOCALAPPDATA%\ConceptGhost-GeometryAssistDiagnostic\Outputs"
if not exist "%OUT%" (
  echo No output folder exists yet.
  pause
  exit /b 2
)
start "" "%OUT%"
