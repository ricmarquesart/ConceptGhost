# ConceptGhost

Camera-aware 3D reference reconstruction from concept art using existing, demonstrated projects rather than reimplementing core solvers from scratch.

## Current status

**Stage 4/14 — Depth Anything V3 baseline / colored point-cloud gate.**

Stages 0–3 are technically proven on the target ComfyUI: inventory and safe framework, Atlas Camera core, protected GeoCalib/OpenCV additions, and a completed learned-camera solve. Stage 4 now adds the public `PozzettiAndrea/ComfyUI-DepthAnythingV3` path so the project can test dense scene reference geometry without replacing the existing Single View / MultiView / Trellis stack.

## Hard non-interference rule

ConceptGhost must not overwrite or re-resolve software used by existing projects. Stage 4 therefore:

- blocks instead of changing an already-installed host package version;
- uses pip resolver **dry-run** first and permits only new additions;
- installs accepted host additions with `--no-deps`;
- reuses an existing correct DA3 checkout untouched, and blocks a conflicting target;
- fingerprints every other `custom_nodes` project before/after;
- avoids comfy-env 0.3.89's workspace-wide installer entirely;
- builds a DA3-only shadow workspace under `C:\ConceptGhost\cache\da3-comfy-env`, then adds only the DA3 runtime junction expected by comfy-env;
- strips only the optional flash/sage CUDA accelerators from the **shadow build config** so the worker retains the host Torch/CUDA ABI and the upstream workflow can fall back to SDPA; the upstream DA3 checkout stays untouched;
- keeps the pixi download cache project-owned under `C:\ConceptGhost\cache\pixi`;
- downloads no DA3 checkpoint during installation;
- copies the public upstream workflows verbatim rather than recreating point-cloud math.

## Permanent upstream references

ConceptGhost follows a **baseline-first** development rule. The exact public revisions used as implementation evidence are pinned in:

- `references/SOURCE_LOCK.json`
- `references/README.md`
- `docs/REFERENCE_CODE_AUDIT.md`

Frozen physical copies are kept in Google Drive under `G:\My Drive\ConceptGhost\References\Upstream_Code`. The full third-party repositories are intentionally not vendored into this repository; GitHub stores the immutable source lock, audit, project-owned adapters, collector, verifier, and tests.

Before a camera/depth/geometry/mesh/DCC stage begins, verify the locked references with:

`tools\VERIFY_REFERENCE_CODE.bat`

If a required mirror is missing or is not at the locked commit, stop that stage until the reference is restored or deliberately re-audited.

## Stage 4 usage

1. Close ComfyUI completely.
2. Run `DA3_BASELINE.bat`. It is a dry-run by default.
3. Review the generated plan and compatibility report.
4. Only after the plan is approved, run `DA3_BASELINE.bat --apply`.
5. Restart ComfyUI and open:

   `C:\ConceptGhost\workflows\reference\da3\advanced_3d.json`

6. Load the same test image and run the **unmodified upstream workflow**.
7. The first run may download `da3_large.safetensors` into `ComfyUI\models\depthanything3`.
8. Gate 4 closes only when the workflow produces a colored PLY point cloud and that point cloud can be inspected as useful scene reference.

## Compatibility evidence

Stage 4 mirrors reports and compatibility evidence to:

- `G:\My Drive\ConceptGhost\Reports\DA3Baseline\<timestamp>`
- `G:\My Drive\ConceptGhost\Tests\Compatibility\Stage4_<timestamp>`
- `G:\My Drive\ConceptGhost\Logs\...`

Persistent storage tracking remains at:

- `C:\ConceptGhost\manifests\storage_usage.txt`
- `G:\My Drive\ConceptGhost\Storage\ConceptGhost_Disk_Usage.txt`

The storage tracker separates project-owned bytes from shared/pre-existing ComfyUI assets and records the DA3-only shadow environment, its project-owned pixi cache, the DA3 checkout/junction, and any checkpoint growth attributable to Stage 4.

## Planned backbone

- Atlas Camera: camera solve, projection geometry and DCC handoff
- Depth Anything 3: depth/camera-space colored point cloud
- MoGe: independent monocular geometry/mesh comparison
- Maya: matched-camera ghost scene for manual blockout

See `docs/STAGE4_DA3_BASELINE.md`, `docs/superpowers/plans/2026-09-15-concept-ghost-roadmap.md`, and `docs/REFERENCE_CODE_AUDIT.md`.
