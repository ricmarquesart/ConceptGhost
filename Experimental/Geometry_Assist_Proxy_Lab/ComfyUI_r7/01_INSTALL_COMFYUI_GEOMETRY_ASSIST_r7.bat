@echo off
setlocal EnableExtensions EnableDelayedExpansion

title ConceptGhost Geometry Assist - ComfyUI Visual Workflow r7
color 0A

echo ================================================================
echo  ConceptGhost Geometry Assist - ComfyUI VISUAL Workflow r7
echo ================================================================
echo.
echo This installer reuses the already validated isolated Geometry Assist
echo models and installs a visible-node ComfyUI workflow.
echo.

set "CG_RUNTIME=%LOCALAPPDATA%\ConceptGhost-GeometryAssistDiagnostic"
set "COMFY_ROOT=%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI"

if not exist "%CG_RUNTIME%\Models\sdxl_base\model_index.json" (
  echo [FAIL] Geometry Assist isolated runtime was not found:
  echo        %CG_RUNTIME%
  echo Install/verify the existing r6 runtime first.
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
  "%COMFY_ROOT%\user\default\workflows"
) do if not exist "%%~D" mkdir "%%~D"

rem Reuse the already-downloaded private models with directory junctions.
call :EnsureJunction "%COMFY_ROOT%\models\diffusers\ConceptGhost_SDXL_Base_1_0" "%CG_RUNTIME%\Models\sdxl_base"
call :EnsureJunction "%COMFY_ROOT%\models\controlnet\ConceptGhost" "%CG_RUNTIME%\Models\controlnet_canny_sdxl_small"
call :EnsureJunction "%COMFY_ROOT%\models\ipadapter\ConceptGhost" "%CG_RUNTIME%\Models\ip_adapter\sdxl_models"
call :EnsureJunction "%COMFY_ROOT%\models\clip_vision\ConceptGhost" "%CG_RUNTIME%\Models\ip_adapter\models\image_encoder"

rem Install/update IPAdapter custom nodes. Other workflow nodes are native ComfyUI.
set "IPA_DIR=%COMFY_ROOT%\custom_nodes\ComfyUI_IPAdapter_plus"
if exist "%IPA_DIR%\IPAdapterPlus.py" (
  echo [OK] IPAdapter nodes already present.
  where git >nul 2>nul && git -C "%IPA_DIR%" pull --ff-only >nul 2>nul
) else (
  echo [INFO] Installing comfyorg/comfyui-ipadapter...
  where git >nul 2>nul
  if errorlevel 1 goto :NoGit
  git clone --depth 1 https://github.com/comfyorg/comfyui-ipadapter.git "%IPA_DIR%"
  if errorlevel 1 (
    echo [FAIL] Could not clone comfyui-ipadapter.
    pause
    exit /b 4
  )
)

goto :AfterIP

:NoGit
echo [FAIL] Git was not found. Install IPAdapter from ComfyUI Manager:
echo        comfyorg/comfyui-ipadapter
pause
exit /b 5

:AfterIP
set "SRC_WF=%~dp0ConceptGhost_Geometry_Assist_MoGe_VISUAL_r7.json"
set "DST_WF=%COMFY_ROOT%\user\default\workflows\ConceptGhost_Geometry_Assist_MoGe_VISUAL_r7.json"
if not exist "%SRC_WF%" (
  echo [FAIL] Workflow file missing next to installer:
  echo        %SRC_WF%
  pause
  exit /b 6
)
copy /Y "%SRC_WF%" "%DST_WF%" >nul
if errorlevel 1 (
  echo [FAIL] Could not install workflow.
  pause
  exit /b 7
)

echo.
echo ================================================================
echo  INSTALL PASS
echo ================================================================
echo Workflow:
echo   %DST_WF%
echo.
echo Models are reused by junction from:
echo   %CG_RUNTIME%\Models
echo.
echo In ComfyUI:
echo   1. Restart ComfyUI.
echo   2. Open workflow: ConceptGhost_Geometry_Assist_MoGe_VISUAL_r7
echo   3. Node 01: choose your image.
echo   4. Click Queue / Run.
echo.
echo All prompts and settings are visible inside the workflow.
echo ================================================================
pause
exit /b 0

:EnsureJunction
set "LINK=%~1"
set "TARGET=%~2"
if not exist "%TARGET%" (
  echo [FAIL] Required source model folder is missing:
  echo        %TARGET%
  pause
  exit /b 20
)
if exist "%LINK%" (
  echo [OK] Existing model link/folder: %LINK%
  exit /b 0
)
mklink /J "%LINK%" "%TARGET%" >nul
if errorlevel 1 (
  echo [FAIL] Could not create model junction:
  echo        %LINK%
  echo        -^> %TARGET%
  pause
  exit /b 21
)
echo [OK] Linked: %LINK%
exit /b 0
