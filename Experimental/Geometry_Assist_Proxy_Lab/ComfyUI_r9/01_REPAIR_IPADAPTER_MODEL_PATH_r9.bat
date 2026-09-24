@echo off
setlocal EnableExtensions EnableDelayedExpansion

title ConceptGhost Geometry Assist - ComfyUI r9 IPAdapter Path Repair
color 0A

echo ================================================================
echo  ConceptGhost Geometry Assist - ComfyUI r9 IPAdapter Repair
echo ================================================================
echo.
echo r9 fixes the remaining r8 issue:
echo   IPAdapter node pack is loaded, but the model is not visible.
echo.
echo Why:
echo   ComfyUI_IPAdapter_plus registers folder_paths.models_dir\ipadapter.
echo   On ComfyUI Desktop this may resolve to ComfyUI-Shared\models\ipadapter.
echo.
echo r9 exposes the same validated ViT-H adapter in BOTH locations.
echo Hardlinks are used first so there is normally no duplicate disk usage.
echo.

set "CG_RUNTIME=%LOCALAPPDATA%\ConceptGhost-GeometryAssistDiagnostic"
set "COMFY_ROOT=%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI"
set "COMFY_SHARED=%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Shared"
set "SOURCE_IP=%CG_RUNTIME%\Models\ip_adapter\sdxl_models\ip-adapter_sdxl_vit-h.safetensors"

if not exist "%SOURCE_IP%" (
  echo [FAIL] Validated source IPAdapter was not found:
  echo        %SOURCE_IP%
  pause
  exit /b 2
)

if not exist "%COMFY_ROOT%\main.py" (
  echo Default ComfyUI Desktop path was not found.
  echo.
  set /p COMFY_ROOT=Paste the FULL ComfyUI folder path: 
)
if not exist "%COMFY_ROOT%\main.py" (
  echo [FAIL] Invalid ComfyUI path: "%COMFY_ROOT%"
  pause
  exit /b 3
)

if not exist "%COMFY_ROOT%\models\ipadapter" mkdir "%COMFY_ROOT%\models\ipadapter"
if not exist "%COMFY_SHARED%\models\ipadapter" mkdir "%COMFY_SHARED%\models\ipadapter"

echo [OK] Source:
echo      %SOURCE_IP%
echo.

call :EnsureModelFile ^
  "%COMFY_ROOT%\models\ipadapter\ip-adapter_sdxl_vit-h.safetensors" ^
  "%SOURCE_IP%"
if errorlevel 1 exit /b !errorlevel!

call :EnsureModelFile ^
  "%COMFY_SHARED%\models\ipadapter\ip-adapter_sdxl_vit-h.safetensors" ^
  "%SOURCE_IP%"
if errorlevel 1 exit /b !errorlevel!

echo.
echo Verifying both ComfyUI model locations...
set "FAIL=0"
call :CheckFile "%COMFY_ROOT%\models\ipadapter\ip-adapter_sdxl_vit-h.safetensors"
call :CheckFile "%COMFY_SHARED%\models\ipadapter\ip-adapter_sdxl_vit-h.safetensors"

if not "%FAIL%"=="0" (
  echo.
  echo [FAIL] IPAdapter model exposure is incomplete.
  pause
  exit /b 20
)

echo.
echo ================================================================
echo  r9 IPADAPTER REPAIR PASS
echo ================================================================
echo.
echo The same model is now visible at:
echo.
echo   INSTALL MODELS:
echo   %COMFY_ROOT%\models\ipadapter\ip-adapter_sdxl_vit-h.safetensors
echo.
echo   SHARED MODELS:
echo   %COMFY_SHARED%\models\ipadapter\ip-adapter_sdxl_vit-h.safetensors
echo.
echo IMPORTANT:
echo   1. FULLY close ComfyUI Desktop.
echo   2. Open ComfyUI Desktop again.
echo   3. Load the existing r8 workflow.
echo   4. The C1 IPAdapter model selector should no longer be red.
echo.
echo You do NOT need a new workflow JSON for this repair.
echo ================================================================
pause
exit /b 0

:EnsureModelFile
set "DEST=%~1"
set "SOURCE=%~2"
if exist "%DEST%" (
  echo [OK] Already present:
  echo      %DEST%
  exit /b 0
)

echo [INFO] Exposing adapter:
echo        %DEST%
mklink /H "%DEST%" "%SOURCE%" >nul 2>nul
if not errorlevel 1 (
  echo [OK] Hardlink created - no duplicate model storage.
  exit /b 0
)

echo [INFO] Hardlink unavailable; copying adapter instead...
copy /B /Y "%SOURCE%" "%DEST%" >nul
if errorlevel 1 (
  echo [FAIL] Could not expose adapter:
  echo        %DEST%
  exit /b 41
)
echo [OK] Adapter copied.
exit /b 0

:CheckFile
if exist "%~1" (
  for %%F in ("%~1") do echo [OK] %%~fF  ^(%%~zF bytes^)
) else (
  echo [MISSING] %~1
  set "FAIL=1"
)
exit /b 0
