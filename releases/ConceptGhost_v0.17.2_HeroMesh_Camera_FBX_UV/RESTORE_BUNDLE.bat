@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul 2>&1
set "HERE=%~dp0"
set "B64=%TEMP%\ConceptGhost_v0172.tar.xz.b64"
set "ARCH=%HERE%ConceptGhost_v0.17.2_HeroMesh_Camera_FBX_UV.tar.xz"
if exist "%B64%" del /q "%B64%"
if exist "%ARCH%" del /q "%ARCH%"
for %%F in ("%HERE%tar_xz_parts\ConceptGhost_v0.17.2_HeroMesh_Camera_FBX_UV.tar.xz.b64.part*") do type "%%~fF" >> "%B64%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$b=[IO.File]::ReadAllText('%B64%'); [IO.File]::WriteAllBytes('%ARCH%',[Convert]::FromBase64String($b))" || exit /b 1
for /f "tokens=*" %%H in ('powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 -LiteralPath '%ARCH%').Hash.ToLowerInvariant()"') do set "SHA=%%H"
if /I not "!SHA!"=="41c468d86bbf736ea73b634c03a31990512350f8398b0ef0f17890784c0c29c3" (
  echo [FAIL] SHA-256 mismatch: !SHA!
  exit /b 2
)
tar -xf "%ARCH%" -C "%HERE%" || exit /b 3
echo [OK] Restored ConceptGhost_v0.17.2_HeroMesh_Camera_FBX_UV
exit /b 0
