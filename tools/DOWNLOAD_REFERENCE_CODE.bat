@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=G:\My Drive\ConceptGhost\References\Upstream_Code"
set "LOG=G:\My Drive\ConceptGhost\References\download_reference_code.log"
set "LOCK_LOCAL=%~dp0..\references\SOURCE_LOCK.json"
set "LOCK_DRIVE=G:\My Drive\ConceptGhost\References\SOURCE_LOCK.json"

if not exist "G:\My Drive" (
  echo ERROR: G:\My Drive is not mounted.
  pause
  exit /b 2
)

where git.exe >nul 2>nul
if errorlevel 1 (
  echo ERROR: git.exe is not on PATH.
  pause
  exit /b 2
)

if not exist "%ROOT%" mkdir "%ROOT%"
if exist "%LOCK_LOCAL%" copy /Y "%LOCK_LOCAL%" "%LOCK_DRIVE%" >nul 2>nul
> "%LOG%" echo ConceptGhost public reference-code collector
>>"%LOG%" echo Started: %DATE% %TIME%
>>"%LOG%" echo This script installs NOTHING. It only downloads public source snapshots.
>>"%LOG%" echo Source lock: %LOCK_LOCAL%
>>"%LOG%" echo.

echo ============================================================
echo ConceptGhost - Public Reference Code Collector
echo ============================================================
echo Destination: %ROOT%
echo No ComfyUI files, Python packages, PATH entries, or model weights are modified.
echo.

call :clone_exact "atlas-camera" "https://github.com/mikejamesvfx/atlas-camera.git" "9f9ff4511154769aa2f8c0bd40387278a69b0078"
call :clone_exact "GeoCalib" "https://github.com/cvg/GeoCalib.git" "97b8968e7798a66bf04fcf791fb535624241bda7"
call :clone_exact "ComfyUI-DepthAnythingV3" "https://github.com/PozzettiAndrea/ComfyUI-DepthAnythingV3.git" "20ef6c8ccf8d57a0ad6f6fa7031739eb8489f2a4"
call :clone_exact "Depth-Anything-3" "https://github.com/ByteDance-Seed/Depth-Anything-3.git" "3d835ec1a5802d64a8b8b15f817a1ab54809bfe4"
call :clone_exact "DA3-blender" "https://github.com/xy-gao/DA3-blender.git" "9d3d0836ead30dd79c5f9320f5b56c4b85073478"
call :clone_exact "MoGe" "https://github.com/microsoft/MoGe.git" "74fbce054ebed49800de42d0ad0e83495065719a"
call :clone_exact "ComfyUI-workflow-templates" "https://github.com/Comfy-Org/workflow_templates.git" "90c71fb78b3726392d010ff62a8e79e92d7296ad"
call :clone_exact "fSpy" "https://github.com/stuffmatic/fSpy.git" "702189ec5acbbd2c8ba492db0e52ecb5fc908f5c"
call :clone_exact "fSpy-Blender" "https://github.com/stuffmatic/fSpy-Blender.git" "eec40b085d45cc623fd379998d85b88de679d4b8"

rem Autodesk MayaUSD: keep documentation and MayaUSD tests as implementation references.
call :clone_sparse "maya-usd-reference" "https://github.com/Autodesk/maya-usd.git" "1245b4b90e56fd7ed41feca4f08dcc11bf222cd4" "doc test/lib/mayaUsd"

rem OpenUSD is very large. Download the concrete public PLY-to-USD example only.
set "USD_DIR=%ROOT%\OpenUSD-selected"
if not exist "%USD_DIR%" mkdir "%USD_DIR%"
set "USD_URL=https://raw.githubusercontent.com/PixarAnimationStudios/OpenUSD/a3d77ff5e1d405b0a5080e7c9f4c6492898fb5c5/extras/imaging/examples/hdParticleField/py3dgsPlyToUsd.py"
echo [OpenUSD-selected] downloading py3dgsPlyToUsd.py
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -UseBasicParsing -Uri '%USD_URL%' -OutFile '%USD_DIR%\py3dgsPlyToUsd.py'; exit 0 } catch { Write-Host $_; exit 1 }"
if errorlevel 1 (
  echo [FAIL] OpenUSD selected example>>"%LOG%"
) else (
  echo [OK] OpenUSD selected example @ a3d77ff5e1d405b0a5080e7c9f4c6492898fb5c5>>"%LOG%"
)

>>"%LOG%" echo.
>>"%LOG%" echo Finished: %DATE% %TIME%

echo.
echo ============================================================
echo Reference collection finished.
echo Review log: %LOG%
echo ============================================================
echo Press any key to close.
pause >nul
exit /b 0

:clone_exact
set "NAME=%~1"
set "URL=%~2"
set "REV=%~3"
set "DST=%ROOT%\%NAME%"
echo [%NAME%] %REV%
if exist "%DST%" (
  if not exist "%DST%\.git" (
    echo [SKIP] %NAME% destination exists but is not a Git checkout. Nothing overwritten.
    echo [SKIP] %NAME% non-git destination already exists>>"%LOG%"
    exit /b 0
  )
  call :guard_stale_lock "%DST%" "%NAME%"
  if errorlevel 1 exit /b 0
  set "EXISTING_URL="
  for /f "delims=" %%R in ('git -C "%DST%" remote get-url origin 2^>nul') do set "EXISTING_URL=%%R"
  if /I not "!EXISTING_URL!"=="%URL%" (
    echo [SKIP] %NAME% existing checkout has different origin. Nothing overwritten.
    echo [SKIP] %NAME% origin mismatch>>"%LOG%"
    exit /b 0
  )
  git -C "%DST%" fetch --filter=blob:none origin %REV% >>"%LOG%" 2>&1
) else (
  git clone --filter=blob:none --no-checkout "%URL%" "%DST%" >>"%LOG%" 2>&1
  if errorlevel 1 (
    echo [FAIL] clone %NAME%
    echo [FAIL] clone %NAME%>>"%LOG%"
    exit /b 0
  )
  git -C "%DST%" fetch --filter=blob:none origin %REV% >>"%LOG%" 2>&1
)
git -C "%DST%" checkout --detach %REV% >>"%LOG%" 2>&1
if errorlevel 1 (
  echo [FAIL] checkout %NAME% %REV%
  echo [FAIL] checkout %NAME% %REV%>>"%LOG%"
) else (
  set "ACTUAL_HEAD="
  for /f "delims=" %%H in ('git -C "%DST%" rev-parse HEAD 2^>nul') do set "ACTUAL_HEAD=%%H"
  if /I not "!ACTUAL_HEAD!"=="%REV%" (
    echo [FAIL] %NAME% HEAD mismatch after checkout
    echo [FAIL] %NAME% expected=%REV% actual=!ACTUAL_HEAD!>>"%LOG%"
  ) else (
    echo [OK] %NAME%
    echo [OK] %NAME% @ %REV%>>"%LOG%"
  )
)
exit /b 0

:clone_sparse
set "NAME=%~1"
set "URL=%~2"
set "REV=%~3"
set "PATHS=%~4"
set "DST=%ROOT%\%NAME%"
echo [%NAME% sparse] %REV%
if exist "%DST%" (
  if not exist "%DST%\.git" (
    echo [SKIP] %NAME% destination exists but is not Git. Nothing overwritten.
    echo [SKIP] %NAME% non-git destination already exists>>"%LOG%"
    exit /b 0
  )
  call :guard_stale_lock "%DST%" "%NAME%"
  if errorlevel 1 exit /b 0
) else (
  git clone --filter=blob:none --no-checkout "%URL%" "%DST%" >>"%LOG%" 2>&1
  if errorlevel 1 (
    echo [FAIL] clone %NAME%
    echo [FAIL] clone %NAME%>>"%LOG%"
    exit /b 0
  )
)
git -C "%DST%" sparse-checkout init --cone >>"%LOG%" 2>&1
git -C "%DST%" sparse-checkout set %PATHS% >>"%LOG%" 2>&1
git -C "%DST%" fetch --filter=blob:none origin %REV% >>"%LOG%" 2>&1
git -C "%DST%" checkout --detach %REV% >>"%LOG%" 2>&1
if errorlevel 1 (
  echo [FAIL] sparse checkout %NAME%
  echo [FAIL] sparse checkout %NAME% @ %REV%>>"%LOG%"
) else (
  echo [OK] %NAME%
  echo [OK] %NAME% @ %REV% paths=%PATHS%>>"%LOG%"
)
exit /b 0

:guard_stale_lock
set "LOCK_REPO=%~1"
set "LOCK_NAME=%~2"
set "LOCK_FILE=%LOCK_REPO%\.git\index.lock"
if not exist "%LOCK_FILE%" exit /b 0

echo [WARN] %LOCK_NAME% has .git\index.lock; checking whether it is stale...
echo [WARN] %LOCK_NAME% index.lock detected>>"%LOG%"

tasklist /FI "IMAGENAME eq git.exe" /NH 2>nul | find /I "git.exe" >nul
if not errorlevel 1 (
  echo [SKIP] %LOCK_NAME% git.exe is active; lock is not removed.
  echo [SKIP] %LOCK_NAME% git.exe is active; index.lock preserved>>"%LOG%"
  exit /b 1
)

set "CG_LOCK_PATH=%LOCK_FILE%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=$env:CG_LOCK_PATH; if (!(Test-Path -LiteralPath $p)) { exit 3 }; try { $age=((Get-Date)-(Get-Item -LiteralPath $p).LastWriteTime).TotalSeconds } catch { exit 2 }; if ($age -ge 120) { exit 0 } else { exit 1 }" >nul 2>&1
set "LOCK_AGE_RC=%ERRORLEVEL%"
if "%LOCK_AGE_RC%"=="3" exit /b 0
if not "%LOCK_AGE_RC%"=="0" (
  if "%LOCK_AGE_RC%"=="1" (
    echo [SKIP] %LOCK_NAME% lock is recent ^(<120 seconds^); nothing removed.
    echo [SKIP] %LOCK_NAME% lock is recent; index.lock preserved>>"%LOG%"
  ) else (
    echo [SKIP] %LOCK_NAME% lock age could not be verified; nothing removed.
    echo [SKIP] %LOCK_NAME% lock age verification failed; index.lock preserved>>"%LOG%"
  )
  exit /b 1
)

del /F /Q "%LOCK_FILE%" >nul 2>&1
if exist "%LOCK_FILE%" (
  echo [FAIL] %LOCK_NAME% stale index.lock could not be removed.
  echo [FAIL] %LOCK_NAME% stale index.lock removal failed>>"%LOG%"
  exit /b 1
)

echo [REPAIRED] %LOCK_NAME% stale index.lock removed safely.
echo [REPAIRED] %LOCK_NAME% stale index.lock removed after age/process checks>>"%LOG%"
exit /b 0
