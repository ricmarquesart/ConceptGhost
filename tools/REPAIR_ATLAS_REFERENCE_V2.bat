@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=G:\My Drive\ConceptGhost\References\Upstream_Code"
set "DST=%ROOT%\atlas-camera-pinned-9f9ff451"
set "REV=9f9ff4511154769aa2f8c0bd40387278a69b0078"
set "URL=https://github.com/mikejamesvfx/atlas-camera.git"
set "LOG=G:\My Drive\ConceptGhost\References\repair_atlas_reference_v2.log"

>"%LOG%" echo ConceptGhost Atlas isolated reference recovery
>>"%LOG%" echo Started: %DATE% %TIME%
>>"%LOG%" echo New target: %DST%
>>"%LOG%" echo Expected commit: %REV%
>>"%LOG%" echo Old broken mirror is intentionally left untouched.
>>"%LOG%" echo.

echo ============================================================
echo ConceptGhost - Atlas Reference Recovery V2
echo ============================================================
echo A fresh sibling mirror will be created at:
echo %DST%
echo.
echo The previous Atlas reference folder is NOT modified or deleted.
echo No ComfyUI installation, Python environment, models, or workflows are changed.
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

if exist "%DST%" goto :verify_existing

echo Creating fresh pinned Atlas mirror...
git clone --filter=blob:none --no-checkout "%URL%" "%DST%" >>"%LOG%" 2>&1
if errorlevel 1 (
  echo ERROR: fresh clone failed. Nothing else was changed.
  goto :fail
)

echo Fetching exact pinned commit...
git -C "%DST%" fetch --filter=blob:none origin %REV% >>"%LOG%" 2>&1
if errorlevel 1 (
  echo ERROR: fetch failed. Review %LOG%
  goto :fail
)

echo Checking out exact pinned commit...
git -C "%DST%" checkout --detach %REV% >>"%LOG%" 2>&1
if errorlevel 1 (
  echo ERROR: checkout failed. Review %LOG%
  goto :fail
)

goto :verify

:verify_existing
echo Fresh target already exists. Verifying it without changing it...
if not exist "%DST%\.git" (
  echo ERROR: target exists but is not a Git checkout. Nothing changed.
  >>"%LOG%" echo ERROR: existing target is not a Git checkout.
  goto :fail
)

:verify
set "HEAD="
for /f "delims=" %%H in ('git -C "%DST%" rev-parse HEAD 2^>nul') do set "HEAD=%%H"
set "ORIGIN="
for /f "delims=" %%R in ('git -C "%DST%" remote get-url origin 2^>nul') do set "ORIGIN=%%R"

if /I not "!ORIGIN!"=="%URL%" (
  echo ERROR: origin mismatch. Nothing changed.
  echo Expected: %URL%
  echo Actual:   !ORIGIN!
  >>"%LOG%" echo ERROR: origin mismatch expected=%URL% actual=!ORIGIN!
  goto :fail
)

if /I not "!HEAD!"=="%REV%" (
  echo ERROR: commit mismatch. Nothing changed.
  echo Expected: %REV%
  echo Actual:   !HEAD!
  >>"%LOG%" echo ERROR: commit mismatch expected=%REV% actual=!HEAD!
  goto :fail
)

echo.
echo [OK] Fresh Atlas reference mirror is pinned correctly.
echo Commit: !HEAD!
echo Path:   %DST%
>>"%LOG%" echo [OK] Atlas fresh mirror @ !HEAD!
>>"%LOG%" echo Path: %DST%
>>"%LOG%" echo Finished: %DATE% %TIME%
echo.
echo Log: %LOG%
echo Press any key to close.
pause >nul
exit /b 0

:fail
>>"%LOG%" echo Finished with ERROR: %DATE% %TIME%
echo.
echo The previous Atlas reference mirror was not modified.
echo Log: %LOG%
echo Press any key to close.
pause >nul
exit /b 2
