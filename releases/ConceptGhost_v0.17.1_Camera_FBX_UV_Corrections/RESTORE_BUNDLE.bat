@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "B64=%TEMP%\ConceptGhost_v0.17.1_bundle.b64"
set "ARCHIVE=%~dp0ConceptGhost_v0.17.1_Camera_FBX_UV_Corrections.tar.xz"
if exist "%B64%" del /q "%B64%"
if exist "%ARCHIVE%" del /q "%ARCHIVE%"
for /f "delims=" %%F in ('dir /b /on "tar_xz_parts\part*.txt"') do type "tar_xz_parts\%%F" >> "%B64%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$b=[IO.File]::ReadAllText('%B64%'); [IO.File]::WriteAllBytes('%ARCHIVE%',[Convert]::FromBase64String($b))"
if errorlevel 1 exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -Command "$h=(Get-FileHash -Algorithm SHA256 '%ARCHIVE%').Hash.ToLower(); if($h -ne '4da22369fa61441173911ea0c5d04e31fc011008333b86d3aa5d6bfa4fe9bced'){Write-Error ('SHA256 mismatch: '+$h); exit 2}"
if errorlevel 1 exit /b 2
tar -xf "%ARCHIVE%" -C "%~dp0"
if errorlevel 1 exit /b 3
echo Restored: ConceptGhost_v0.17.1_Camera_FBX_UV_Corrections
endlocal
