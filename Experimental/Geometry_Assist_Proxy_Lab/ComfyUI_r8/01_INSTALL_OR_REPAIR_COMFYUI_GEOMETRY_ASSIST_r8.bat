@echo off
setlocal EnableExtensions EnableDelayedExpansion

title ConceptGhost Geometry Assist - ComfyUI r8 Repair Installer
color 0A

echo ================================================================
echo  ConceptGhost Geometry Assist - ComfyUI VISUAL Workflow r8
echo ================================================================
echo.
echo r8 repairs the two setup problems visible in r7:
echo   1. IPAdapter custom nodes not active / restart required.
echo   2. CLIP Vision and ControlNet exposed with non-canonical paths.
echo.
echo The large models are REUSED from the validated isolated runtime.
echo No model re-download is required if r6 was already installed.
echo.

set "CG_RUNTIME=%LOCALAPPDATA%\ConceptGhost-GeometryAssistDiagnostic"
set "COMFY_ROOT=%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI"

if not exist "%CG_RUNTIME%\Models\sdxl_base\model_index.json" (
  echo [FAIL] Isolated Geometry Assist runtime not found:
  echo        %CG_RUNTIME%
  echo Install/verify r6 first.
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

echo [OK] ComfyUI: %COMFY_ROOT%
echo [OK] Geometry Assist runtime: %CG_RUNTIME%
echo.

for %%D in (
  "%COMFY_ROOT%\models\diffusers"
  "%COMFY_ROOT%\models\controlnet"
  "%COMFY_ROOT%\models\ipadapter"
  "%COMFY_ROOT%\models\clip_vision"
  "%COMFY_ROOT%\custom_nodes"
  "%COMFY_ROOT%\user\default\workflows"
) do if not exist "%%~D" mkdir "%%~D"

rem ----------------------------------------------------------------
rem 1) SDXL diffusers directory. This path already worked in r7.
rem ----------------------------------------------------------------
call :EnsureJunction ^
  "%COMFY_ROOT%\models\diffusers\ConceptGhost_SDXL_Base_1_0" ^
  "%CG_RUNTIME%\Models\sdxl_base"
if errorlevel 1 exit /b !errorlevel!

rem ----------------------------------------------------------------
rem 2) Expose SINGLE model files at canonical ComfyUI filenames.
rem    Hardlink = no duplicate disk usage on the same volume.
rem    If hardlink is impossible, fall back to file copy.
rem ----------------------------------------------------------------
call :EnsureModelFile ^
  "%COMFY_ROOT%\models\controlnet\controlnet-canny-sdxl-1.0-small.safetensors" ^
  "%CG_RUNTIME%\Models\controlnet_canny_sdxl_small\diffusion_pytorch_model.fp16.safetensors"
if errorlevel 1 exit /b !errorlevel!

call :EnsureModelFile ^
  "%COMFY_ROOT%\models\ipadapter\ip-adapter_sdxl_vit-h.safetensors" ^
  "%CG_RUNTIME%\Models\ip_adapter\sdxl_models\ip-adapter_sdxl_vit-h.safetensors"
if errorlevel 1 exit /b !errorlevel!

call :EnsureModelFile ^
  "%COMFY_ROOT%\models\clip_vision\CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors" ^
  "%CG_RUNTIME%\Models\ip_adapter\models\image_encoder\model.safetensors"
if errorlevel 1 exit /b !errorlevel!

rem ----------------------------------------------------------------
rem 3) Install / repair IPAdapter custom nodes.
rem ----------------------------------------------------------------
set "IPA_DIR=%COMFY_ROOT%\custom_nodes\ComfyUI_IPAdapter_plus"
set "IPA_ALT=%COMFY_ROOT%\custom_nodes\comfyui-ipadapter"

if exist "%IPA_DIR%\IPAdapterPlus.py" goto :IPFound
if exist "%IPA_ALT%\IPAdapterPlus.py" (
  set "IPA_DIR=%IPA_ALT%"
  goto :IPFound
)

echo [INFO] IPAdapter node pack is missing. Installing official package...
where git >nul 2>nul
if errorlevel 1 (
  echo [FAIL] Git is not installed or not on PATH.
  echo.
  echo In ComfyUI Manager install:
  echo   ComfyUI_IPAdapter_plus
  echo Then restart ComfyUI and run this installer again.
  pause
  exit /b 10
)

git clone --depth 1 https://github.com/comfyorg/comfyui-ipadapter.git "%IPA_DIR%"
if errorlevel 1 (
  echo [FAIL] Could not clone comfyorg/comfyui-ipadapter.
  echo You may install ComfyUI_IPAdapter_plus from ComfyUI Manager instead.
  pause
  exit /b 11
)

:IPFound
echo [OK] IPAdapter node pack: %IPA_DIR%

rem No requirements.txt is currently required by the node package.
rem Compile only as a lightweight static sanity check when python is available.
if exist "%COMFY_ROOT%\python_embeded\python.exe" (
  "%COMFY_ROOT%\python_embeded\python.exe" -m compileall -q "%IPA_DIR%" >nul 2>nul
)

rem ----------------------------------------------------------------
rem 4) Install visual workflow.
rem ----------------------------------------------------------------
set "SRC_WF=%~dp0ConceptGhost_Geometry_Assist_MoGe_VISUAL_r8.json"
set "DST_WF=%COMFY_ROOT%\user\default\workflows\ConceptGhost_Geometry_Assist_MoGe_VISUAL_r8.json"

if not exist "%SRC_WF%" (
  echo [FAIL] Workflow file is missing next to this installer:
  echo        %SRC_WF%
  pause
  exit /b 12
)

copy /Y "%SRC_WF%" "%DST_WF%" >nul
if errorlevel 1 (
  echo [FAIL] Could not install workflow:
  echo        %DST_WF%
  pause
  exit /b 13
)

rem ----------------------------------------------------------------
rem 5) Final verification.
rem ----------------------------------------------------------------
set "VERIFY_FAIL=0"
call :CheckFile "%COMFY_ROOT%\models\controlnet\controlnet-canny-sdxl-1.0-small.safetensors"
call :CheckFile "%COMFY_ROOT%\models\ipadapter\ip-adapter_sdxl_vit-h.safetensors"
call :CheckFile "%COMFY_ROOT%\models\clip_vision\CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"
call :CheckFile "%IPA_DIR%\IPAdapterPlus.py"
call :CheckFile "%DST_WF%"

if not "%VERIFY_FAIL%"=="0" (
  echo.
  echo [FAIL] One or more required files are still missing.
  pause
  exit /b 20
)

echo.
echo ================================================================
echo  r8 INSTALL / REPAIR PASS
echo ================================================================
echo.
echo Canonical model files now visible to ComfyUI:
echo   controlnet\controlnet-canny-sdxl-1.0-small.safetensors
echo   ipadapter\ip-adapter_sdxl_vit-h.safetensors
echo   clip_vision\CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors
echo.
echo Workflow:
echo   %DST_WF%
echo.
echo IMPORTANT:
echo   ComfyUI MUST be restarted after installing/repairing custom nodes
echo   or model paths. If ComfyUI shows "Apply Changes", click it.
echo   Otherwise fully close and reopen ComfyUI Desktop.
echo.
echo After restart:
echo   1. Load ConceptGhost_Geometry_Assist_MoGe_VISUAL_r8
echo   2. Choose the image in node 01
echo   3. Click Run / Queue
echo.
echo Do NOT use the old r7 workflow for this test.
echo ================================================================
pause
exit /b 0

:EnsureJunction
set "LINK=%~1"
set "TARGET=%~2"
if not exist "%TARGET%" (
  echo [FAIL] Missing source directory:
  echo        %TARGET%
  exit /b 31
)
if exist "%LINK%\model_index.json" (
  echo [OK] SDXL directory already exposed.
  exit /b 0
)
if exist "%LINK%" (
  echo [INFO] Existing path found: %LINK%
  echo        Leaving it untouched.
  exit /b 0
)
mklink /J "%LINK%" "%TARGET%" >nul
if errorlevel 1 (
  echo [FAIL] Could not create directory junction:
  echo        %LINK%
  exit /b 32
)
echo [OK] Linked SDXL directory.
exit /b 0

:EnsureModelFile
set "DEST=%~1"
set "SOURCE=%~2"
if not exist "%SOURCE%" (
  echo [FAIL] Missing source model:
  echo        %SOURCE%
  exit /b 40
)
if exist "%DEST%" (
  echo [OK] Model already exists:
  echo      %DEST%
  exit /b 0
)
echo [INFO] Exposing model:
echo        %DEST%
mklink /H "%DEST%" "%SOURCE%" >nul 2>nul
if not errorlevel 1 (
  echo [OK] Hardlink created - no duplicate model storage.
  exit /b 0
)
echo [INFO] Hardlink unavailable; copying model file instead...
copy /B /Y "%SOURCE%" "%DEST%" >nul
if errorlevel 1 (
  echo [FAIL] Could not expose model:
  echo        %DEST%
  exit /b 41
)
echo [OK] Model copied.
exit /b 0

:CheckFile
if not exist "%~1" (
  echo [MISSING] %~1
  set "VERIFY_FAIL=1"
) else (
  echo [OK] %~1
)
exit /b 0
