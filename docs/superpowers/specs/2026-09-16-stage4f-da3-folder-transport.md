# ConceptGhost Stage 4F — DA3 Folder-Path Transport Backport

## Problem proven by Gate 4P

ComfyUI Desktop host serves:
`C:\Users\rmarq\AppData\Local\Comfy-Desktop\ComfyUI-Shared\output`

The isolated DA3 worker resolves:
`C:\Users\rmarq\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\output`

The DA3 upstream `DA3_SavePointCloud` uses `folder_paths.get_output_directory()`.
Therefore the worker writes `pointcloud_0000.ply` to its private/default output path,
while the browser viewer asks the host `/view?type=output`, which serves the Desktop
shared output path and returns HTTP 404.

## Upstream basis

`comfy-env` v0.3.89 sends only `sys_paths` to the worker at startup.
Newer upstream `comfy-env` transports the host's resolved `folder_paths` state and,
before pack code runs, applies:
- `folder_paths.set_input_directory(...)`
- `folder_paths.set_output_directory(...)`
- `folder_paths.set_temp_directory(...)`

Stage 4F backports only the required path-alignment behavior into the
ConceptGhost-owned DA3 isolated worker. It does not upgrade or edit the global
`comfy-env` package, so Pixal3D/Trellis/global ComfyUI packages remain untouched.

## Scope

Dry-run:
1. Read the newest successful Stage 4P diagnostic from Google Drive.
2. Require `classification.hypothesis == "worker_output_mismatch"`.
3. Require an explicit live-host `output_arg` and `input_arg`.
4. Require the worker Python/environment to be under
   `C:\ConceptGhost\cache\da3-comfy-env`.
5. Discover the isolated worker site-packages directory.
6. Refuse conflicts at the two planned bootstrap filenames.
7. Report the exact two worker-site files and one project config file that would
   be created.

Apply:
1. Snapshot host `pip freeze`.
2. Snapshot non-DA3 custom-node metadata.
3. Write only:
   - `C:\ConceptGhost\config\da3_host_paths.json`
   - `<DA3 worker site-packages>\conceptghost_da3_worker_paths.py`
   - `<DA3 worker site-packages>\conceptghost_da3_worker_paths.pth`
4. The `.pth` imports the bootstrap module at Python startup.
5. The bootstrap acts only when:
   - the interpreter is the expected DA3 isolated environment, and
   - argv contains `persistent_worker.py`, or the explicit probe environment
     variable `CG_DA3_PATH_PROBE=1` is set.
6. The bootstrap inserts the known ComfyUI source root, imports `folder_paths`,
   and applies the host input/output directories captured from Gate 4P.
7. Probe the isolated worker and require:
   - worker input == host input
   - worker output == host output
8. Verify host `pip freeze` unchanged.
9. Verify protected custom nodes unchanged.

## Explicit non-goals

- No `pip install`.
- No global `comfy-env` upgrade/downgrade.
- No edits to `ComfyUI-DepthAnythingV3` upstream files.
- No edits to `comfy-3d-viewers`.
- No changes to Torch/Torchvision/NumPy/Kornia/Transformers.
- No moving/deleting the already generated stray PLY.
- No junction/symlink replacement of the global ComfyUI output folder.

## Acceptance

After apply + ComfyUI restart, a probe must show the DA3 worker resolves the same
input/output directories as the host Desktop process. Then the unchanged upstream
`advanced_3d.json` is rerun. The new PLY must be created under
`ComfyUI-Shared\output`, and `DA3_PreviewPointCloud` must load it without 404.
