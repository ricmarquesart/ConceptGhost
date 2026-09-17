@echo off
setlocal EnableExtensions
set "HERE=%~dp0"
if not exist "%HERE%ConceptGhost_v0.17.2_HeroMesh_Camera_FBX_UV\INSTALL_CONCEPTGHOST_V0.17.2.bat" (
  echo Run RESTORE_BUNDLE.bat first.
  exit /b 1
)
call "%HERE%ConceptGhost_v0.17.2_HeroMesh_Camera_FBX_UV\INSTALL_CONCEPTGHOST_V0.17.2.bat"
exit /b %ERRORLEVEL%
