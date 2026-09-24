@echo off
setlocal EnableExtensions

title Verify ConceptGhost Geometry Assist r9 IPAdapter
color 0B

set "COMFY_ROOT=%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI"
set "COMFY_SHARED=%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Shared"
set "CG_RUNTIME=%LOCALAPPDATA%\ConceptGhost-GeometryAssistDiagnostic"
set "NAME=ip-adapter_sdxl_vit-h.safetensors"

echo ================================================================
echo  Verify Geometry Assist r9 IPAdapter paths
echo ================================================================
echo.

set "FAIL=0"
call :Check "%CG_RUNTIME%\Models\ip_adapter\sdxl_models\%NAME%"
call :Check "%COMFY_ROOT%\models\ipadapter\%NAME%"
call :Check "%COMFY_SHARED%\models\ipadapter\%NAME%"

echo.
if "%FAIL%"=="0" (
  echo [PASS] Adapter exists in source + install models + shared models.
  echo Fully restart ComfyUI Desktop before loading the r8 workflow.
) else (
  echo [FAIL] At least one adapter location is missing.
)
echo.
pause
exit /b %FAIL%

:Check
if exist "%~1" (
  for %%F in ("%~1") do echo [OK] %%~fF  ^(%%~zF bytes^)
) else (
  echo [MISSING] %~1
  set "FAIL=1"
)
exit /b 0
