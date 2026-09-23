# Lotus Depth Diagnostic Lab

Experimental, isolated Lotus diagnostic workflow for visual comparison with MoGe. This package is not part of the authoritative ConceptGhost geometry pipeline.

## Model choice

The lab uses the official Lotus discriminative checkpoints:
- `jingheya/lotus-depth-d-v2-0-disparity` for relative disparity.
- `jingheya/lotus-normal-d-v1-1` for native aligned surface normals.

Lotus-2 is intentionally not used because its official repository requires at least 40 GB of GPU VRAM. The target ConceptGhost workstation has substantially less VRAM, so Lotus-2 is not an appropriate local diagnostic baseline.

## Isolation

The installer creates `%LOCALAPPDATA%\ConceptGhost-LotusDiagnostic` and puts the Python runtime, Torch/CUDA wheel environment, Lotus source, Hugging Face cache, models, temporary files, logs and diagnostic outputs there.

It does **not** install Python packages into ComfyUI. It does **not** write models into ComfyUI model folders. It does **not** modify the MoGe runtime or any SingleView, MultiView, Trellis or official ConceptGhost files.

The only host-side files are:
- `ComfyUI\custom_nodes\ConceptGhost_Lotus_Diagnostic`
- `ComfyUI\user\default\workflows\Lotus_Depth_Diagnostic.json`

## Disk budget

For the full official discriminative depth + native-normal setup, reserve **18 GB free before installation**. Expected steady-state use is roughly **11–13 GB**, with transient installation/download space potentially reaching **14–16 GB**. All runtime/download caches are contained under the isolated runtime root and are removable by the uninstaller.

## Entry points

1. `01_INSTALL_LOTUS_DIAGNOSTIC.bat`
2. `02_VERIFY_LOTUS_DIAGNOSTIC.bat`
3. Restart ComfyUI and open `Lotus_Depth_Diagnostic.json`.
4. To remove the experiment, run `03_UNINSTALL_LOTUS_DIAGNOSTIC.bat`.

## Diagnostic outputs

Every run is written below `%LOCALAPPDATA%\ConceptGhost-LotusDiagnostic\Outputs\<run_id>` and can include:
- original image
- Lotus native disparity preview
- normalized disparity grayscale
- heatmap
- inverse-disparity relative-depth proxy
- quantized depth bands
- contours
- depth/disparity edges
- Lotus native normal map
- relative point-cloud PLY and front/side/top/3D preview when enabled
- statistics JSON
- manifest JSON
- raw `.npy` arrays when enabled
- comparison mosaic

The point cloud is **relative/non-metric** and uses assumed intrinsics only for visualization. It has no authority over ConceptGhost geometry.

## Distribution

Canonical evaluation bundle is mirrored in Google Drive under `P10_Lab_Baseline_Multiview_Completion/Lotus_Diagnostic_Lab`.

Bundle name: `ConceptGhost_Lotus_Diagnostic_Isolated_FULL_r3.zip`\n\n### Installer r2 hotfix\n\nThe first installer build had two Windows PowerShell bootstrap defects: the embeddable Python pip probe could terminate before `get-pip.py`, and a single ComfyUI candidate could be treated as a scalar string so `$valid[0]` resolved to the character `C`. r2 fixes both issues and adds regression tests. Existing partial `%LOCALAPPDATA%\\ConceptGhost-LotusDiagnostic` state from the failed first attempt can be resumed safely.

This GitHub folder is a registration/authority record for the isolated experiment. The official P9/P10 workflow is not modified by this lab.


### Installer r3 hotfix — Windows no-symlink model materialization

r3 removes Hugging Face `snapshot_download` from model installation. On Windows without Developer Mode/admin privileges, r2 could fail with `WinError 1314` while creating snapshot symlinks after multi-gigabyte files had already downloaded.

r3 writes ordinary files directly to `Models\depth` and `Models\normal`, supports resumable `.part` downloads, reuses valid complete/partial blobs from the failed r2 owned cache when possible, verifies declared size and LFS SHA-256 metadata, and removes the obsolete owned cache only after both models are complete.

Recovery path: re-run `01_INSTALL_LOTUS_DIAGNOSTIC.bat`. No manual cleanup, Administrator mode, or Windows Developer Mode is required by the installer.
