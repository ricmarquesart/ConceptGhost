@echo off
setlocal EnableExtensions

title Verify ConceptGhost Geometry Assist ComfyUI r8
color 0B

set "COMFY_ROOT=%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI"
if not exist "%COMFY_ROOT%\main.py" (
  set /p COMFY_ROOT=Paste the FULL ComfyUI folder path: 
)

echo ================================================================
echo  Verify Geometry Assist ComfyUI r8
echo ================================================================

set "FAIL=0"

call :Check "%COMFY_ROOT%\models\diffusers\ConceptGhost_SDXL_Base_1_0\model_index.json"
call :Check "%COMFY_ROOT%\models\controlnet\controlnet-canny-sdxl-1.0-small.safetensors"
call :Check "%COMFY_ROOT%\models\ipadapter\ip-adapter_sdxl_vit-h.safetensors"
call :Check "%COMFY_ROOT%\models\clip_vision\CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"
call :CheckOneOf "%COMFY_ROOT%\custom_nodes\ComfyUI_IPAdapter_plus\IPAdapterPlus.py" "%COMFY_ROOT%\custom_nodes\comfyui-ipadapter\IPAdapterPlus.py"
call :Check "%COMFY_ROOT%\user\default\workflows\ConceptGhost_Geometry_Assist_MoGe_VISUAL_r8.json"

echo.
if "%FAIL%"=="0" (
  echo [PASS] All r8 files are present.
  echo.
  echo IMPORTANT: this does not prove the IPAdapter nodes are loaded in the
  echo currently running ComfyUI process. After node installation you MUST
  echo click "Apply Changes" if shown, or fully restart ComfyUI Desktop.
  echo.
  echo After restart load the r8 workflow. There should be no red UNKNOWN
  echo nodes and no Missing Models warning for the three canonical files.
) else (
  echo [FAIL] One or more required files are missing.
)
echo.
pause
exit /b %FAIL%

:Check
if exist "%~1" (
  echo [OK] %~1
) else (
  echo [MISSING] %~1
  set "FAIL=1"
)
exit /b 0

:CheckOneOf
if exist "%~1" (
  echo [OK] %~1
  exit /b 0
)
if exist "%~2" (
  echo [OK] %~2
  exit /b 0
)
echo [MISSING] IPAdapterPlus.py
set "FAIL=1"
exit /b 0
