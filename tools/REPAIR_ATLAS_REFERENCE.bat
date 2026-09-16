@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "DST=G:\My Drive\ConceptGhost\References\Upstream_Code\atlas-camera"
set "REV=9f9ff4511154769aa2f8c0bd40387278a69b0078"
set "URL=https://github.com/mikejamesvfx/atlas-camera.git"
set "LOG=G:\My Drive\ConceptGhost\References\repair_atlas_reference.log"
set "LOCK_FILE=%DST%\.git\index.lock"

>"%LOG%" echo ConceptGhost Atlas reference repair
>>"%LOG%" echo Started: %DATE% %TIME%
>>"%LOG%" echo Target: %DST%
>>"%LOG%" echo Expected commit: %REV%
>>"%LOG%" echo.

echo ============================================================
echo ConceptGhost - Repair Atlas Reference Mirror
echo ============================================================
echo This touches ONLY the Google Drive reference mirror:
echo %DST%
echo It does NOT touch ComfyUI, custom_nodes, Python, models, or workflows.
echo.

if not exist "G:\My Drive" (
  echo ERROR: G:\My Drive is not mounted.
  >>"%LOG%" echo ERROR: G:\My Drive is not mounted.
  goto :fail
)

where git.exe >nul 2>nul
if errorlevel 1 (
  echo ERROR: git.exe is not on PATH.
  >>"%LOG%" echo ERROR: git.exe is not on PATH.
  goto :fail
)

if not exist "%DST%\.git" (
  echo ERROR: Atlas reference mirror is not a Git checkout.
  >>"%LOG%" echo ERROR: target is not a Git checkout.
  goto :fail
)

set "ORIGIN="
for /f "delims=" %%R in ('git -C "%DST%" remote get-url origin 2^>nul') do set "ORIGIN=%%R"
if /I not "!ORIGIN!"=="%URL%" (
  echo ERROR: Atlas mirror origin is different. Nothing changed.
  echo Actual: !ORIGIN!
  >>"%LOG%" echo ERROR: origin mismatch: !ORIGIN!
  goto :fail
)

if exist "%LOCK_FILE%" (
  echo Found index.lock. Checking whether it is safe to remove...
  tasklist /FI "IMAGENAME eq git.exe" /NH 2>nul | find /I "git.exe" >nul
  if not errorlevel 1 (
    echo STOP: git.exe is currently active. Lock preserved.
    >>"%LOG%" echo STOP: git.exe active; lock preserved.
    goto :fail
  )

  set "CG_LOCK_PATH=%LOCK_FILE%"
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=$env:CG_LOCK_PATH; if (!(Test-Path -LiteralPath $p)) { exit 3 }; try { $age=((Get-Date)-(Get-Item -LiteralPath $p).LastWriteTime).TotalSeconds } catch { exit 2 }; if ($age -ge 120) { exit 0 } else { exit 1 }" >nul 2>&1
  set "LOCK_RC=!ERRORLEVEL!"
  if "!LOCK_RC!"=="3" goto :after_lock
  if not "!LOCK_RC!"=="0" (
    if "!LOCK_RC!"=="1" (
      echo STOP: index.lock is less than 120 seconds old. Lock preserved.
      >>"%LOG%" echo STOP: recent lock preserved.
    ) else (
      echo STOP: could not verify lock age. Lock preserved.
      >>"%LOG%" echo STOP: lock age verification failed.
    )
    goto :fail
  )

  del /F /Q "%LOCK_FILE%" >nul 2>&1
  if exist "%LOCK_FILE%" (
    echo ERROR: stale index.lock could not be removed.
    >>"%LOG%" echo ERROR: stale lock removal failed.
    goto :fail
  )
  echo [REPAIRED] stale index.lock removed.
  >>"%LOG%" echo [REPAIRED] stale index.lock removed after age/process checks.
)

:after_lock
echo Fetching exact Atlas reference commit...
git -C "%DST%" fetch --filter=blob:none origin %REV% >>"%LOG%" 2>&1
if errorlevel 1 (
  echo ERROR: fetch failed. Review %LOG%
  goto :fail
)

git -C "%DST%" checkout --detach %REV% >>"%LOG%" 2>&1
if errorlevel 1 (
  echo ERROR: checkout failed. Review %LOG%
  goto :fail
)

set "HEAD="
for /f "delims=" %%H in ('git -C "%DST%" rev-parse HEAD 2^>nul') do set "HEAD=%%H"
if /I not "!HEAD!"=="%REV%" (
  echo ERROR: HEAD mismatch.
  echo Expected: %REV%
  echo Actual:   !HEAD!
  >>"%LOG%" echo ERROR: expected=%REV% actual=!HEAD!
  goto :fail
)

echo.
echo [OK] Atlas reference mirror is pinned correctly.
echo Commit: !HEAD!
>>"%LOG%" echo [OK] Atlas reference mirror @ !HEAD!
>>"%LOG%" echo Finished: %DATE% %TIME%
echo Log: %LOG%
echo.
echo Press any key to close.
pause >nul
exit /b 0

:fail
>>"%LOG%" echo Finished with ERROR: %DATE% %TIME%
echo.
echo No ComfyUI project files were changed.
echo Log: %LOG%
echo Press any key to close.
pause >nul
exit /b 2
