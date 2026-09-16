# ConceptGhost

Camera-aware 3D reference reconstruction from concept art using existing, demonstrated projects rather than reimplementing core solvers from scratch.

## Current status

**Stage 3/14 — Atlas learned-camera dependency compatibility gate passed; upstream reference lock is now part of the project infrastructure.**

Stage 2 Atlas Camera core has been proven to load in the target ComfyUI. Stage 3 installed the learned-camera dependencies through a protected compatibility gate and the Atlas quickstart completed a real solve on the target machine.

## Hard non-interference rule

ConceptGhost must not overwrite or re-resolve the environment used by existing Single View / MultiView workflows.

Stage 3 therefore:

- never upgrades/downgrades Torch, Torchvision, NumPy, Kornia, Transformers, xformers, ComfyUI packages, or other existing packages;
- never writes to non-Atlas `custom_nodes` projects;
- never modifies existing workflow JSON files;
- reuses existing GeoCalib or `cv2` if they already work;
- **blocks** instead of reinstalling when an existing GeoCalib/OpenCV distribution looks broken;
- installs missing GeoCalib from a pinned Git commit with `--no-deps`;
- installs missing OpenCV from a pinned wheel with `--no-deps --only-binary=:all:`;
- snapshots the entire pip freeze plus every non-Atlas custom-node tree before/after;
- fails the compatibility gate if any pre-existing package changes, disappears, or any non-Atlas custom-node tree changes.

The installer intentionally leaves the existing `kornia` version unchanged. Atlas documents `<0.8.3` as a coexistence repair for LTXVideo, but changing a shared Kornia install would violate this project's preservation rule. We first test GeoCalib against the already-working environment and only reconsider Kornia if there is direct evidence of incompatibility.

## Permanent upstream references

ConceptGhost follows a **baseline-first** development rule. The exact public revisions used as implementation evidence are pinned in:

- `references/SOURCE_LOCK.json`
- `references/README.md`
- `docs/REFERENCE_CODE_AUDIT.md`

Frozen physical copies are kept in Google Drive under `G:\My Drive\ConceptGhost\References\Upstream_Code`. The full third-party repositories are intentionally not vendored into this repository; GitHub stores the immutable source lock, audit, project-owned adapters, collector, verifier, and tests.

Before a camera/depth/geometry/mesh/DCC stage begins, verify the locked references with:

`tools\VERIFY_REFERENCE_CODE.bat`

If a required mirror is missing or is not at the locked commit, stop that stage until the reference is restored or deliberately re-audited.

## Stage 3 usage

1. **Close ComfyUI completely.**
2. Run `ATLAS_CAMERA_DEPS.bat` by double-click or command line. Default is dry-run.
3. Review the plan. It should show only additive GeoCalib/OpenCV actions or reuse actions.
4. If there are no blockers, run:

   `ATLAS_CAMERA_DEPS.bat --apply`

5. Restart ComfyUI.
6. Open `C:\ConceptGhost\workflows\reference\atlas\atlas_input_quickstart_workflow.json`.
7. Load an image and run the learned solve.

The first actual learned solve may download GeoCalib model weights through Torch Hub. The storage tracker records the GeoCalib cache baseline so only new cache growth is charged to ConceptGhost.

## Compatibility evidence

Every Stage 3 run mirrors evidence to:

- `G:\My Drive\ConceptGhost\Reports\AtlasCameraDeps\<timestamp>`
- `G:\My Drive\ConceptGhost\Tests\Compatibility\Stage3_<timestamp>`
- `G:\My Drive\ConceptGhost\Logs\...`

Evidence includes before/after pip freeze, environment probes, non-Atlas custom-node fingerprints, deltas, install manifest, runtime import probe, and command log.

## Storage tracking

Persistent storage ledger:

- `C:\ConceptGhost\manifests\storage_usage.txt`
- `G:\My Drive\ConceptGhost\Storage\ConceptGhost_Disk_Usage.txt`

The tracker separates project-owned bytes from shared/pre-existing ComfyUI assets and includes Stage 3 package bytes plus only the growth of the GeoCalib model cache above its pre-install baseline.

## Planned backbone

- Atlas Camera: camera solve, projection geometry and DCC handoff
- Depth Anything 3: depth/camera-space point cloud path
- MoGe: independent monocular geometry/mesh path
- Maya: matched-camera ghost scene for manual blockout

See `docs/superpowers/plans/2026-09-15-concept-ghost-roadmap.md`, `docs/STAGE3_COMPATIBILITY_GATE.md`, and `docs/REFERENCE_CODE_AUDIT.md`.
