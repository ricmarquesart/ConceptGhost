# DR9R r11 — Versioned Entrypoint + Nested Installer Compatibility Hotfix

Date: 2026-09-23

## Trigger

The first target-machine run of the published r10 package exposed a packaging-only entrypoint defect before any new P10 runtime logic executed:

- `03_INSTALL_ALL.bat` referenced `Installer\install_dr10.ps1`, but that file did not exist.
- `04_VERIFY_INSTALL.bat` had the same latent defect for `Installer\verify_dr10.ps1`.
- The BAT printed a false-looking trailing PASS because `powershell.exe` returned through the batch flow in a way the relabel-only package did not guard correctly.

The underlying r10 nested Gate5/Gate6 compatibility correction remains valid.

## r11 correction

r11 is built from the frozen r9 package plus the validated r10 nested-installer hotfix, but now also:

- ships real `Installer\install_dr11.ps1`;
- ships real `Installer\verify_dr11.ps1`;
- makes `03_INSTALL_ALL.bat` point to the real r11 installer;
- makes `04_VERIFY_INSTALL.bat` point to the real r11 verifier;
- fails package validation if either BAT target is missing or mismatched;
- preserves CRLF on Windows BAT entrypoints;
- keeps only the two public numbered workflows;
- keeps the Gate5/Gate6 current-Production private verifier fixture behavior.

## Scope

Packaging/installer compatibility only. P9 authority, P10 geometry code, route authoring, WAN, COLMAP reconstruction, MoGe diagnostics, storage, immutable attempt handling and Maya non-overwrite contracts are unchanged.

Gate 7 remains blocked until r11 passes target-machine runtime acceptance.
