# Stage 4 — DA3 Baseline

Stage 4 installs the **public ComfyUI-DepthAnythingV3 workflow path** while keeping the existing ComfyUI projects protected.

## Acceptance target

The gate is not closed by installation alone. It closes only when the unmodified upstream `advanced_3d.json` workflow runs on a source image and produces a colored `.ply` point cloud that is useful enough to inspect as scene reference.

## Pinned upstream

- Node pack: `PozzettiAndrea/ComfyUI-DepthAnythingV3`
- New-install commit: `20ef6c8ccf8d57a0ad6f6fa7031739eb8489f2a4`
- Host bridge pins required by that node pack: `comfy-env==0.3.89`, `comfy-3d-viewers==0.2.44`
- Reference workflows copied verbatim: `advanced.json`, `advanced_3d.json`, `bas_relief.json`

An existing correct upstream DA3 checkout is **reused untouched**. ConceptGhost does not reset, checkout, update, or overwrite it.

## Non-interference policy

`DA3_BASELINE.bat` is a dry-run by default. Before apply it inventories the host Python and asks pip's resolver what the pinned bridge packages would add. Apply is blocked if the resolver proposes changing any package that already exists.

When apply is approved:

1. only missing, resolver-approved host bridge packages are added with `--no-deps`;
2. the DA3 node pack is cloned only if absent;
3. every other `custom_nodes` tree is fingerprinted before/after and must remain unchanged;
4. ConceptGhost **does not call** comfy-env 0.3.89's normal `install()` / `install --dir` path, because that release rebuilds the workspace globally across discovered packs;
5. instead, a shadow ComfyUI containing only DA3's isolation config is built under `C:\ConceptGhost\cache`, with `COMFY_ENV_ROOT` set only for that subprocess;
6. the shadow config omits optional `flash_attn` / `sageattention` CUDA accelerators so the DA3 worker keeps the host Torch/CUDA ABI and uses the upstream `auto` → SDPA fallback; the real DA3 checkout is not modified;
7. after the project-owned worker is materialized, ConceptGhost adds only a runtime directory junction at comfy-env's expected DA3 env path; existing worker environments and the global pixi manifest are not rebuilt;
8. the subprocess-only pixi cache is directed to `C:\ConceptGhost\cache\pixi`;
9. no model checkpoint is downloaded during installation;
10. storage deltas and compatibility evidence are written to local manifests and mirrored by the BAT to Google Drive.

If any existing Python package, protected custom node, or pre-existing comfy-env environment changes unexpectedly, the gate fails closed.

## User flow

1. Close ComfyUI completely.
2. Run `DA3_BASELINE.bat` with no arguments.
3. Review the dry-run / let ChatGPT read the Drive report.
4. Only when approved, run `DA3_BASELINE.bat --apply`.
5. Restart ComfyUI.
6. Open `C:\ConceptGhost\workflows\reference\da3\advanced_3d.json`.
7. Load the same source image used for the Atlas test and run the workflow unchanged.
8. The loader may download `da3_large.safetensors` into `ComfyUI\models\depthanything3` on first use.
9. Confirm `DA3_SavePointCloud` produces a colored PLY and the point-cloud preview opens.

## Storage

Stage 4 separately tracks:

- managed DA3 repository bytes;
- host bridge package bytes;
- the project-owned DA3 comfy-env workspace (already included inside `C:\ConceptGhost`);
- growth of comfy-env's pixi home;
- project-owned pixi cache under `C:\ConceptGhost`;
- only the growth of `ComfyUI\models\depthanything3` above the pre-Stage-4 baseline.

Shared/pre-existing folders are never attributed wholesale to ConceptGhost.
