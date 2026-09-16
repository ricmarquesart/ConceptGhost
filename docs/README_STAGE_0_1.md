# ConceptGhost — Stage 0/1 Bootstrap

This package implements only the safe foundation of the ConceptGhost roadmap.

## What this package does

- inventories existing ComfyUI, Python packages, DA3/MoGe/Atlas assets, Maya locations, and disk free space;
- hashes discovered DA3/MoGe model files by default;
- creates the controlled `C:\ConceptGhost` directory tree;
- records every managed file in `install_manifest.json`;
- records per-write disk accounting in JSON and CSV;
- preserves existing `config.yml` and writes a refreshed `config.default.yml` instead;
- provides a conservative uninstall that keeps pre-existing or user-modified files.

## What it deliberately does NOT do yet

It does not install or download Atlas Camera, GeoCalib, DA3, MoGe, model weights, SAM, inpainting packages, or any Maya plugin. It does not modify PATH or permanent environment variables.

## Windows launcher behavior

`SETUP.bat` now keeps the Command Prompt window open at the end of the run, including error cases, so it can be safely started by double-click. Press any key only after reviewing the displayed result.

## Recommended first run

1. Extract the package somewhere temporary.
2. Open Command Prompt in that folder.
3. Run `SETUP.bat` with no arguments. This is a dry run.
4. Review the printed operations.
5. Run `SETUP.bat --apply` to create the Stage 0/1 framework.
6. Review:
   - `C:\ConceptGhost\manifests\preinstall_inventory.json`
   - `C:\ConceptGhost\manifests\preinstall_python_packages.txt`
   - `C:\ConceptGhost\manifests\preinstall_disk.json`
   - `C:\ConceptGhost\manifests\install_manifest.json`
   - `C:\ConceptGhost\manifests\disk_ledger.json`
   - `C:\ConceptGhost\manifests\disk_ledger.csv`
   - `C:\ConceptGhost\logs\setup_report.json`

## ComfyUI Desktop detection

The inventory reads the current Comfy Desktop metadata at `%APPDATA%\Comfy Desktop\installations.json` and supports the managed Desktop layout (`<installPath>\ComfyUI\.venv\Scripts\python.exe`) plus the pre-migration `envs\default` fallback. This discovery is read-only; ConceptGhost never edits Comfy Desktop metadata.

## If ComfyUI is not auto-detected

Run the inventory helper with an explicit root, for example:

`INVENTORY.bat --comfyui-root "D:\AI\ComfyUI_windows_portable"`

Both the portable distribution root and the nested `ComfyUI` application root are accepted.

## Hashing large checkpoints

Inventory hashes discovered DA3/MoGe checkpoint files because future cleanup must know exactly which files existed before ConceptGhost. If you only want a fast preliminary scan, run:

`INVENTORY.bat --no-model-hashes`

Do a full hash inventory before Stage 2 installs anything.

## Uninstall safety

`UNINSTALL.bat` is also dry-run by default. `UNINSTALL.bat --apply` removes only files recorded as owned by ConceptGhost. Output is preserved by default. A managed file whose hash changed after installation is preserved and reported. `--force` exists but should not be used casually.

## Current gate

Stage 0/1 is complete only when the inventory correctly identifies the actual ComfyUI installation and all known pre-existing models/components. Atlas Camera installation belongs to Stage 2 and must not begin until this inventory is reviewed.
