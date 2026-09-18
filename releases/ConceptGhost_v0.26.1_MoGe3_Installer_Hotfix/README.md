# ConceptGhost v0.26.1 — MoGe-3 Installer Hotfix

This hotfix fixes the Windows PowerShell 5.1 failure observed immediately after the private Python 3.11.9 installation.

## Fixes

- Renames the native-command argument parameter from `$Args` to `$CommandArgs` so it does not collide with PowerShell's automatic `$args` variable.
- Native stderr no longer aborts an otherwise healthy command under `$ErrorActionPreference = "Stop"`; success/failure is decided from the native process exit code.
- All pip/Torch/MoGe/verification commands remain explicitly bound to the private runtime Python:
  `%LOCALAPPDATA%\ConceptGhost-MoGeRuntime-v1\python\python.exe`.
- No ComfyUI, Single View, Multi View, MoGe-2, PATH, global Python, Torch or CUDA environment is modified.

## User action

If v0.26 and `VERIFY_V026_INSTALLED.bat` already passed, do not reinstall the clean workflow. Use the v0.26.1 complete package from Google Drive and run only:

`INSTALL_MOGE3_RUNTIME.bat`

The already-installed private Python 3.11.9 can be reused.

## Package hashes

- COMPLETE ZIP SHA256: `926765e5ebbcd06b6ca2410db880a476447c362c3ae7fc2fb858808c164cb007`
- SOURCE ZIP SHA256: `fd916ba1b73c41e8b38984471669ecad3c8c0b0e3cd607a64b885e254b4b9033`
